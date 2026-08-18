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


def obtenir_appel(appel_id):
    conn = connexion_app()
    ligne = conn.execute("SELECT * FROM appels WHERE id = ?", (appel_id,)).fetchone()
    conn.close()
    return dict(ligne) if ligne else None
