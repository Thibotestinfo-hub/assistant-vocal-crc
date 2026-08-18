"""
Connexions aux deux bases du projet.

- data/gtfs.db : régénérée à chaque rechargement du GTFS (Étape 2). Lecture
  seule depuis les outils.
- data/assistant.db : l'état propre à l'application (déclarations d'objets
  perdus, demandes de rappel...). Ne doit JAMAIS être recréée depuis zéro
  comme gtfs.db — ce sont de vraies données saisies par de vrais appelants.
  Les tables sont créées avec IF NOT EXISTS, jamais DROP.
"""

import sqlite3
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent.parent
DB_GTFS_PATH = RACINE / "data" / "gtfs.db"
DB_APP_PATH = RACINE / "data" / "assistant.db"

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
-- complète telle que reçue (voir assistant/backoffice/appels.py) :
-- le format exact n'a pas pu être vérifié contre la documentation au
-- moment d'écrire ce schéma, donc rien n'est perdu même si les
-- quelques champs extraits ci-dessous se révèlent incomplets.
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
"""

NOMS_OUTILS = [
    "rechercher_arret", "horaires_theoriques", "rechercher_information",
    "enregistrer_objet_perdu", "demander_rappel", "transferer_agent",
]


def connexion_gtfs():
    conn = sqlite3.connect(DB_GTFS_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def connexion_app():
    conn = sqlite3.connect(DB_APP_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA_APP)
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
