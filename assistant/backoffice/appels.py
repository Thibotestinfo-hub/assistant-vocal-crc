"""
Historique des appels — Étape 6, point 1 de la méthode.

ElevenLabs envoie un webhook ("post_call_transcription") à la fin de
chaque conversation. Je n'ai pas pu vérifier le format exact de ce
webhook contre la documentation officielle (bloquée depuis mon
environnement de travail au moment d'écrire ce fichier) : par
prudence, `enregistrer_appel` conserve donc toujours la charge brute
complète, en plus des quelques champs dont le nom est raisonnablement
sûr (conversation_id, agent_id, status). À vérifier et enrichir dès
qu'un vrai webhook aura été reçu et inspecté — voir TODO plus bas.
"""

import json
from datetime import datetime

from assistant.outils.db import connexion_app


def enregistrer_appel(charge_brute: dict):
    """Insère (ou met à jour si déjà vu) un appel à partir de la charge
    du webhook ElevenLabs. Ne lève jamais d'exception sur un format
    inattendu : un appel dont on ne reconnaît aucun champ est quand
    même stocké, pour ne perdre aucune donnée reçue."""
    # TODO(vérifié à l'usage) : ces chemins sont une hypothèse. Certains
    # webhooks ElevenLabs enveloppent la charge utile dans une clé
    # "data" ; on tente les deux formes sans faire d'hypothèse plus forte.
    donnees = charge_brute.get("data", charge_brute) if isinstance(charge_brute, dict) else {}
    conversation_id = donnees.get("conversation_id")
    agent_id = donnees.get("agent_id")
    statut = donnees.get("status")

    conn = connexion_app()
    conn.execute(
        """
        INSERT INTO appels (cree_le, conversation_id, agent_id, statut, donnees_brutes)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(conversation_id) DO UPDATE SET
            statut = excluded.statut,
            donnees_brutes = excluded.donnees_brutes
        """,
        (
            datetime.now().isoformat(timespec="seconds"),
            conversation_id, agent_id, statut,
            json.dumps(charge_brute, ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()


def lister_appels(limite=100):
    conn = connexion_app()
    lignes = conn.execute(
        "SELECT id, cree_le, conversation_id, agent_id, statut FROM appels "
        "ORDER BY id DESC LIMIT ?",
        (limite,),
    ).fetchall()
    conn.close()
    return [dict(l) for l in lignes]


def lister_appels_avec_details(limite=100):
    """Comme lister_appels, mais avec la charge brute et les évaluations
    de chaque appel déjà chargées — utilisé par la page back-office
    consolidée, qui affiche tout sur un seul écran (accordéon HTML natif,
    sans rechargement de page par appel)."""
    conn = connexion_app()
    appels = conn.execute(
        "SELECT id, cree_le, conversation_id, agent_id, statut, donnees_brutes FROM appels "
        "ORDER BY id DESC LIMIT ?",
        (limite,),
    ).fetchall()
    resultat = []
    for a in appels:
        a = dict(a)
        evals = conn.execute(
            "SELECT cree_le, qualite, note FROM evaluations_appels "
            "WHERE appel_id = ? ORDER BY id DESC",
            (a["id"],),
        ).fetchall()
        a["evaluations"] = [dict(e) for e in evals]
        resultat.append(a)
    conn.close()
    return resultat


def compter_appels():
    conn = connexion_app()
    n = conn.execute("SELECT COUNT(*) AS n FROM appels").fetchone()["n"]
    conn.close()
    return n


def resumer_evaluations():
    """Renvoie (nb_bonnes, nb_total) sur la dernière évaluation de chaque
    appel évalué — un appel évalué plusieurs fois ne compte qu'une fois,
    pour son avis le plus récent."""
    conn = connexion_app()
    lignes = conn.execute(
        """
        SELECT qualite FROM evaluations_appels e
        WHERE e.id = (
            SELECT id FROM evaluations_appels e2
            WHERE e2.appel_id = e.appel_id
            ORDER BY id DESC LIMIT 1
        )
        """
    ).fetchall()
    conn.close()
    total = len(lignes)
    bonnes = sum(1 for l in lignes if l["qualite"] == "bonne")
    return bonnes, total


def obtenir_appel(appel_id):
    conn = connexion_app()
    ligne = conn.execute("SELECT * FROM appels WHERE id = ?", (appel_id,)).fetchone()
    conn.close()
    return dict(ligne) if ligne else None


def enregistrer_evaluation(appel_id, qualite, note=None):
    """qualite vaut 'bonne' ou 'mauvaise'. N'écrase jamais un avis
    précédent : chaque évaluation s'ajoute à l'historique de l'appel."""
    conn = connexion_app()
    conn.execute(
        "INSERT INTO evaluations_appels (appel_id, cree_le, qualite, note) VALUES (?, ?, ?, ?)",
        (appel_id, datetime.now().isoformat(timespec="seconds"), qualite, note or None),
    )
    conn.commit()
    conn.close()


def lister_evaluations(appel_id):
    conn = connexion_app()
    lignes = conn.execute(
        "SELECT cree_le, qualite, note FROM evaluations_appels "
        "WHERE appel_id = ? ORDER BY id DESC",
        (appel_id,),
    ).fetchall()
    conn.close()
    return [dict(l) for l in lignes]
