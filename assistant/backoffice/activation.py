"""
Activation progressive des outils — Étape 6, point 4 : pouvoir n'ouvrir
qu'un seul cas d'usage au départ (ex. la FAQ), puis les autres au fil
des semaines, plus un interrupteur général pour tout couper d'un coup.

Le choix technique : un outil désactivé renvoie une erreur HTTP (503),
pas une réponse habillée en "rien trouvé". Ce n'est pas une facilité,
c'est ce qui a été vérifié en conditions réelles aujourd'hui (Étape 5) :
à chaque fois qu'un outil a échoué techniquement (404, 422...), l'agent
vocal a basculé proprement vers la sortie sans jamais inventer de
réponse. On réutilise ce comportement déjà éprouvé plutôt que d'essayer
de fabriquer une fausse réponse "vide" différente pour chacun des 6
contrats de sortie (voir spec §4), au risque de s'y contredire.
"""

from fastapi import HTTPException

from assistant.outils.db import NOMS_OUTILS, connexion_app


def est_actif(outil):
    conn = connexion_app()
    ligne_generale = conn.execute(
        "SELECT actif FROM activation_outils WHERE outil = 'tous'"
    ).fetchone()
    ligne_outil = conn.execute(
        "SELECT actif FROM activation_outils WHERE outil = ?", (outil,)
    ).fetchone()
    conn.close()
    if not ligne_generale or not ligne_generale["actif"]:
        return False
    return bool(ligne_outil and ligne_outil["actif"])


def lister_activations():
    conn = connexion_app()
    lignes = {
        r["outil"]: bool(r["actif"])
        for r in conn.execute("SELECT outil, actif FROM activation_outils").fetchall()
    }
    conn.close()
    return {
        "tous": lignes.get("tous", True),
        "outils": {nom: lignes.get(nom, True) for nom in NOMS_OUTILS},
    }


def basculer(outil):
    """Inverse l'état actif/inactif de outil ('tous' ou un nom d'outil)."""
    conn = connexion_app()
    conn.execute(
        "UPDATE activation_outils SET actif = 1 - actif WHERE outil = ?", (outil,)
    )
    conn.commit()
    conn.close()


def verifier_outil_actif(nom_outil):
    """Fabrique une dépendance FastAPI pour un outil donné : à utiliser
    comme Depends(verifier_outil_actif("rechercher_arret")) sur chaque
    route d'outil."""
    def dependance():
        if not est_actif(nom_outil):
            raise HTTPException(
                status_code=503,
                detail=f"{nom_outil} temporairement désactivé depuis le back-office",
            )
    return dependance
