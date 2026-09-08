"""
Outil `demander_rappel`. Contrat : spec §4.

conversation_id (optionnel) : comme pour enregistrer_satisfaction, doit
être fourni par ElevenLabs via la variable dynamique
{{system__conversation_id}}, à déclarer dans le corps de la requête
webhook de cet outil côté configuration de l'agent. Permet au
back-office de relier une demande de rappel à l'appel dont elle vient
(badge "à rappeler" dans le tableau des appels) — sans cette variable
câblée, la demande reste enregistrée normalement, seulement sans lien
visible vers l'appel d'origine.
"""

from assistant.outils.db import connexion_app, horodatage

MOTIFS_VALIDES = {"amende", "reclamation", "tad", "scolaire", "hors_perimetre", "demande_agent"}


def demander_rappel(telephone, motif, resume, nom=None, email=None, opt_in_marketing=False, conversation_id=None):
    if motif not in MOTIFS_VALIDES:
        return {"succes": False, "erreur": f"motif inconnu : {motif!r}"}
    if not telephone or not resume:
        return {"succes": False, "erreur": "telephone et resume sont obligatoires"}

    conn = connexion_app()
    curseur = conn.execute(
        """
        INSERT INTO demandes_rappel
            (cree_le, telephone, nom, email, motif, resume, opt_in_marketing, conversation_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            horodatage(),
            telephone, nom, email, motif, resume, int(bool(opt_in_marketing)), conversation_id,
        ),
    )
    conn.commit()
    demande_id = curseur.lastrowid
    conn.close()

    return {"succes": True, "demande_id": demande_id}
