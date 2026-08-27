"""
Connexions aux deux bases du projet.

- data/gtfs.db : régénérée à chaque rechargement du GTFS (Étape 2). Lecture
  seule depuis les outils.
- data/etat/assistant.db : l'état propre à l'application (déclarations
  d'objets perdus, demandes de rappel...). Ne doit JAMAIS être recréée
  depuis zéro comme gtfs.db — ce sont de vraies données saisies par de
  vrais appelants. Les tables sont créées avec IF NOT EXISTS, jamais DROP.

  Sur Clever Cloud, data/etat/ est monté comme un espace de stockage
  persistant ("FS Bucket") qui survit aux redéploiements — contrairement
  au reste de data/, remis à neuf à chaque déploiement. Sous-dossier
  dédié (pas directement data/) pour ne pas entrer en conflit avec les
  fichiers déjà versionnés (config.yaml, corpus_index.json) : Clever
  Cloud ignore le montage si le dossier cible n'est pas vide.

  Piège vérifié en conditions réelles : le log de déploiement Clever
  Cloud affiche "Mounting bucket ... on /data/etat" (chemin absolu),
  ce qui a d'abord fait croire que le montage se faisait à la racine du
  système de fichiers plutôt que dans le dossier de l'application. Faux :
  ce chemin absolu n'est pas accessible depuis l'application elle-même
  (PermissionError constatée à l'usage). Cette ligne de log décrit le
  montage vu par l'orchestrateur Clever Cloud, pas ce que voit
  l'application une fois démarrée — la documentation avait raison, le
  montage se fait bien relativement au dossier de l'application.
"""

import sqlite3
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent.parent
DB_GTFS_PATH = RACINE / "data" / "gtfs.db"
DB_APP_PATH = RACINE / "data" / "etat" / "assistant.db"

_SCHEMA_APP = """
CREATE TABLE IF NOT EXISTS objets_perdus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cree_le TEXT NOT NULL,
    nature TEXT NOT NULL,
    description TEXT NOT NULL,
    ligne TEXT,
    sens TEXT,
    date_perte TEXT NOT NULL,
    creneau_horaire TEXT NOT NULL,
    lieu TEXT NOT NULL,
    arret_id TEXT,
    nom TEXT NOT NULL,
    telephone TEXT NOT NULL,
    email TEXT,
    opt_in_marketing INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS demandes_rappel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cree_le TEXT NOT NULL,
    telephone TEXT NOT NULL,
    nom TEXT,
    email TEXT,
    motif TEXT NOT NULL,
    resume TEXT NOT NULL,
    opt_in_marketing INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS transferts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cree_le TEXT NOT NULL,
    motif TEXT NOT NULL,
    resume TEXT NOT NULL
);

-- Étape 6 : historique des appels, alimenté par le webhook de fin
-- d'appel envoyé par ElevenLabs. donnees_brutes conserve la charge
-- complète telle que reçue (voir assistant/backoffice/appels.py).
-- Le format a depuis été vérifié sur un vrai payload : les colonnes de
-- traçabilité (durée, coût, minutes ASR/TTS, modèles, outils) sont
-- ajoutées après coup via _migrer_colonnes_manquantes, pas ici — SQLite
-- ne permet pas d'ajouter une colonne dans CREATE TABLE IF NOT EXISTS
-- sur une table qui existe déjà en production.
CREATE TABLE IF NOT EXISTS appels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cree_le TEXT NOT NULL,
    conversation_id TEXT UNIQUE,
    agent_id TEXT,
    statut TEXT,
    donnees_brutes TEXT NOT NULL
);

-- Étape 6, point 4 : activation progressive des outils. La clé "tous"
-- est l'interrupteur général (voir assistant/backoffice/activation.py) :
-- s'il est coupé, plus aucun outil ne répond, quel que soit son propre
-- réglage.
CREATE TABLE IF NOT EXISTS activation_outils (
    outil TEXT PRIMARY KEY,
    actif INTEGER NOT NULL DEFAULT 1
);

-- Étape 6, point 2 : évaluation humaine d'un appel a posteriori (bonne
-- ou mauvaise réponse, avec une note libre). Plusieurs évaluations
-- possibles par appel — jamais de mise à jour qui écraserait un avis
-- précédent, seulement des ajouts, pour garder l'historique complet.
CREATE TABLE IF NOT EXISTS evaluations_appels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appel_id INTEGER NOT NULL,
    cree_le TEXT NOT NULL,
    qualite TEXT NOT NULL CHECK (qualite IN ('bonne', 'mauvaise')),
    note TEXT
);

-- Règles de prononciation ajoutées depuis le back-office, en plus de
-- data/prononciation.pls (versionné, mais réécrit à neuf à chaque
-- déploiement comme tout data/ hors data/etat/ — voir l'en-tête de ce
-- fichier). Une règle ajoutée ici prévaut sur celle du fichier pour le
-- même nom (voir assistant/ingestion/prononciation.py), et survit aux
-- déploiements puisqu'elle vit dans data/etat/, comme les autres
-- tables de cette base.
CREATE TABLE IF NOT EXISTS regles_prononciation (
    grapheme TEXT PRIMARY KEY,
    alias TEXT NOT NULL,
    cree_le TEXT NOT NULL
);

-- Satisfaction déclarée par l'appelant lui-même (à distinguer de
-- evaluations_appels, qui est l'avis de l'équipe sur la qualité d'un
-- appel a posteriori). Enregistrée par l'outil enregistrer_satisfaction,
-- appelé PENDANT l'appel (avant le webhook de fin d'appel qui crée la
-- ligne dans "appels") : table à part, jointe par conversation_id à
-- l'affichage plutôt qu'une colonne dans "appels", pour ne pas dépendre
-- de l'ordre d'arrivée entre les deux (voir assistant/backoffice/appels.py).
CREATE TABLE IF NOT EXISTS satisfaction_appels (
    conversation_id TEXT PRIMARY KEY,
    satisfait INTEGER NOT NULL,
    cree_le TEXT NOT NULL
);
"""

NOMS_OUTILS = [
    "rechercher_arret", "horaires_theoriques", "rechercher_information",
    "enregistrer_objet_perdu", "demander_rappel", "transferer_agent",
]

# Traçabilité par appel (CLAUDE.md, contrainte non négociable) : ajoutées
# après coup à une table déjà en production, via ALTER TABLE — un CREATE
# TABLE IF NOT EXISTS ne les aurait pas ajoutées aux bases existantes.
# Toutes nullables : les appels enregistrés avant ce changement n'ont pas
# cette donnée, et un futur format de webhook inconnu ne doit jamais faire
# échouer l'enregistrement (voir enregistrer_appel).
_COLONNES_TRACABILITE = {
    "duree_secs": "INTEGER",
    "cout_usd": "REAL",
    "minutes_asr": "REAL",
    "minutes_tts": "REAL",
    "modeles_llm": "TEXT",   # JSON : détail tokens par modèle (parfois plusieurs par appel)
    "tokens_llm": "INTEGER",  # somme, toutes catégories et modèles confondus
    "outils_utilises": "TEXT",  # JSON : liste des outils réellement appelés
    "voix_utilisees": "TEXT",  # JSON : liste des voice_id ElevenLabs utilisés
}


def _migrer_colonnes_manquantes(conn):
    colonnes_existantes = {r["name"] for r in conn.execute("PRAGMA table_info(appels)").fetchall()}
    for nom, type_sql in _COLONNES_TRACABILITE.items():
        if nom not in colonnes_existantes:
            conn.execute(f"ALTER TABLE appels ADD COLUMN {nom} {type_sql}")


def connexion_gtfs():
    conn = sqlite3.connect(DB_GTFS_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def connexion_app():
    # En local, data/etat/ n'existe pas forcément encore (sur Clever
    # Cloud, c'est le point de montage du FS Bucket, déjà présent).
    DB_APP_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_APP_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA_APP)
    _migrer_colonnes_manquantes(conn)
    # Une ligne par outil, plus "tous" (l'interrupteur général), toutes
    # actives par défaut. INSERT OR IGNORE : ne touche jamais un réglage
    # déjà choisi par l'équipe CRC.
    for cle in [*NOMS_OUTILS, "tous"]:
        conn.execute(
            "INSERT OR IGNORE INTO activation_outils (outil, actif) VALUES (?, 1)",
            (cle,),
        )
    conn.commit()
    return conn
