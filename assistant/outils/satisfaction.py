"""
Outil `enregistrer_satisfaction` — capte l'avis de l'appelant lui-même en
fin de conversation, à distinguer de l'évaluation faite a posteriori par
l'équipe (assistant/backoffice/appels.py, evaluations_appels). Contrat
proposé le 27/08/2026, pas encore dans docs/spec-assistant-vocal-v0-revisee.md
(à ajouter une fois la formulation validée avec l'équipe).

conversation_id doit être fourni par ElevenLabs via la variable dynamique
{{system__conversation_id}}, à déclarer dans le corps de la requête webhook
de cet outil côté configuration de l'agent (ElevenLabs expose cette
variable pour ce cas précis — voir la doc "Dynamic variables").
"""

from assistant.outils.db import connexion_app, horodatage


def enregistrer_satisfaction(conversation_id, satisfait):
    if not conversation_id:
        # Ne devrait jamais arriver si la variable dynamique
        # {{system__conversation_id}} est bien câblée côté ElevenLabs (voir
        # docstring plus haut) — loggé pour être visible dans les logs
        # Clever Cloud si ça arrive quand même, plutôt que d'échouer en
        # silence sans aucune trace.
        print("enregistrer_satisfaction : conversation_id manquant, rien enregistré", flush=True)
        return {"succes": False}
    conn = connexion_app()
    conn.execute(
        "INSERT INTO satisfaction_appels (conversation_id, satisfait, cree_le) VALUES (?, ?, ?) "
        "ON CONFLICT(conversation_id) DO UPDATE SET satisfait = excluded.satisfait",
        (conversation_id, int(bool(satisfait)), horodatage()),
    )
    conn.commit()
    conn.close()
    return {"succes": True}
