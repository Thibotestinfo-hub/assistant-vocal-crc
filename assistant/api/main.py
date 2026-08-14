"""
API des outils de l'assistant vocal. Chaque endpoint /outils/* correspond
exactement à un outil décrit dans docs/spec-assistant-vocal-v0-revisee.md, §4.

Lancer en local : uv run uvicorn assistant.api.main:app --reload
"""

from fastapi import Depends, FastAPI

from assistant.api.auth import verifier_jeton
from assistant.api.schemas import (
    HorairesRequete, HorairesReponse,
    InformationRequete, InformationReponse,
    ObjetPerduRequete, ObjetPerduReponse,
    RappelRequete, RappelReponse,
    RechercherArretRequete, RechercherArretReponse,
    TransfertRequete, TransfertReponse,
)
from assistant.outils.horaires_theoriques import horaires_theoriques
from assistant.outils.objets_perdus import enregistrer_objet_perdu
from assistant.outils.rappels import demander_rappel
from assistant.outils.rechercher_arret import rechercher_arret
from assistant.outils.rechercher_information import rechercher_information
from assistant.outils.transfert import transferer_agent

app = FastAPI(title="Assistant vocal — API des outils")


@app.get("/sante")
def sante():
    """Pas d'authentification requise : sert juste à vérifier que l'API
    est en ligne et joignable (voir méthode, Étape 3)."""
    return {"statut": "bonjour"}


@app.post("/outils/rechercher_arret", response_model=RechercherArretReponse,
          dependencies=[Depends(verifier_jeton)])
def route_rechercher_arret(requete: RechercherArretRequete):
    return rechercher_arret(requete.texte, requete.commune, requete.ligne)


@app.post("/outils/horaires_theoriques", response_model=HorairesReponse,
          dependencies=[Depends(verifier_jeton)])
def route_horaires_theoriques(requete: HorairesRequete):
    return horaires_theoriques(
        requete.arret_id, requete.ligne, requete.direction,
        requete.type, requete.date, requete.nb,
    )


@app.post("/outils/enregistrer_objet_perdu", response_model=ObjetPerduReponse,
          dependencies=[Depends(verifier_jeton)])
def route_enregistrer_objet_perdu(requete: ObjetPerduRequete):
    return enregistrer_objet_perdu(**requete.model_dump())


@app.post("/outils/demander_rappel", response_model=RappelReponse,
          dependencies=[Depends(verifier_jeton)])
def route_demander_rappel(requete: RappelRequete):
    return demander_rappel(**requete.model_dump())


@app.post("/outils/transferer_agent", response_model=TransfertReponse,
          dependencies=[Depends(verifier_jeton)])
def route_transferer_agent(requete: TransfertRequete):
    return transferer_agent(requete.motif, requete.resume)


@app.post("/outils/rechercher_information", response_model=InformationReponse,
          dependencies=[Depends(verifier_jeton)])
def route_rechercher_information(requete: InformationRequete):
    return rechercher_information(requete.question, requete.categorie)
