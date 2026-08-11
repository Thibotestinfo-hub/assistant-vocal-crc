"""
Outil `demander_rappel`. Contrat : spec §4.
"""

from datetime import datetime

from assistant.outils.db import connexion_app

MOTIFS_VALIDES = {"amende", "reclamation", "tad", "scolaire", "hors_perimetre", "demande_agent"}


def demander_rappel(telephone, motif, resume, nom=None, email=None, opt_in_marketing=False):
    if motif not in MOTIFS_VALIDES:
        return {"succes": False, "erreur": f"motif inconnu : {motif!r}"}
    if not telephone or not resume:
        return {"succes": False, "erreur": "telephone et resume sont obligatoires"}

    conn = connexion_app()
    curseur = conn.execute(
        """
        INSERT INTO demandes_rappel (cree_le, telephone, nom, email, motif, resume, opt_in_marketing)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now().isoformat(timespec="seconds"),
            telephone, nom, email, motif, resume, int(bool(opt_in_marketing)),
        ),
    )
    conn.commit()
    demande_id = curseur.lastrowid
    conn.close()

    return {"succes": True, "demande_id": demande_id}
