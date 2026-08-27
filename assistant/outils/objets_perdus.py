"""
Outil `enregistrer_objet_perdu`. Contrat : spec §4.
"""

from assistant.outils.db import connexion_app, horodatage

CHAMPS_OBLIGATOIRES = [
    "nature", "description", "date_perte", "creneau_horaire", "lieu",
    "nom", "telephone", "opt_in_marketing",
]


def enregistrer_objet_perdu(**donnees):
    manquants = [c for c in CHAMPS_OBLIGATOIRES if donnees.get(c) is None]
    if manquants:
        return {"succes": False, "erreur": f"champs manquants : {', '.join(manquants)}"}

    conn = connexion_app()
    curseur = conn.execute(
        """
        INSERT INTO objets_perdus
            (cree_le, nature, description, ligne, sens, date_perte, creneau_horaire,
             lieu, arret_id, nom, telephone, email, opt_in_marketing)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            horodatage(),
            donnees["nature"], donnees["description"],
            donnees.get("ligne"), donnees.get("sens"),
            donnees["date_perte"], donnees["creneau_horaire"], donnees["lieu"],
            donnees.get("arret_id"), donnees["nom"], donnees["telephone"],
            donnees.get("email"), int(bool(donnees["opt_in_marketing"])),
        ),
    )
    conn.commit()
    declaration_id = curseur.lastrowid
    conn.close()

    return {"succes": True, "declaration_id": declaration_id}
