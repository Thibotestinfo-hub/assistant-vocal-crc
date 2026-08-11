"""
Outil `transferer_agent` — uniquement CRC ouvert. Contrat : spec §4.

Pas de vraie téléphonie à ce stade (Étape 5) : on se contente de logger
l'intention de transfert, qui sera exploitée par la plateforme vocale.
"""

from datetime import datetime

from assistant.outils.db import connexion_app


def transferer_agent(motif, resume):
    conn = connexion_app()
    curseur = conn.execute(
        "INSERT INTO transferts (cree_le, motif, resume) VALUES (?, ?, ?)",
        (datetime.now().isoformat(timespec="seconds"), motif, resume),
    )
    conn.commit()
    transfert_id = curseur.lastrowid
    conn.close()

    return {"succes": True, "transfert_id": transfert_id}
