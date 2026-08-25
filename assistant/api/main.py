"""
API des outils de l'assistant vocal. Chaque endpoint /outils/* correspond
exactement à un outil décrit dans docs/spec-assistant-vocal-v0-revisee.md, §4.

Lancer en local : uv run uvicorn assistant.api.main:app --reload
"""

from typing import Literal

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from assistant.api.auth import verifier_acces_backoffice, verifier_jeton, verifier_jeton_requete
from assistant.api.schemas import (
    HorairesRequete, HorairesReponse,
    InformationRequete, InformationReponse,
    ObjetPerduRequete, ObjetPerduReponse,
    RappelRequete, RappelReponse,
    RechercherArretRequete, RechercherArretReponse,
    TransfertRequete, TransfertReponse,
)
from assistant.backoffice.activation import basculer, lister_activations, verifier_outil_actif
from assistant.backoffice.appels import (
    compter_appels, enregistrer_appel, enregistrer_evaluation, lister_appels_avec_details,
    resumer_evaluations, resumer_tracabilite,
)
from assistant.backoffice.exports import (
    exporter_contacts_marketing, exporter_demandes_rappel, exporter_objets_perdus,
)
from assistant.backoffice.page import page_backoffice
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
          dependencies=[Depends(verifier_jeton), Depends(verifier_outil_actif("rechercher_arret"))])
def route_rechercher_arret(requete: RechercherArretRequete):
    return rechercher_arret(requete.texte, requete.commune, requete.ligne)


@app.post("/outils/horaires_theoriques", response_model=HorairesReponse,
          dependencies=[Depends(verifier_jeton), Depends(verifier_outil_actif("horaires_theoriques"))])
def route_horaires_theoriques(requete: HorairesRequete):
    return horaires_theoriques(
        requete.arret_id, requete.ligne, requete.direction,
        requete.type, requete.date, requete.nb,
    )


@app.post("/outils/enregistrer_objet_perdu", response_model=ObjetPerduReponse,
          dependencies=[Depends(verifier_jeton), Depends(verifier_outil_actif("enregistrer_objet_perdu"))])
def route_enregistrer_objet_perdu(requete: ObjetPerduRequete):
    return enregistrer_objet_perdu(**requete.model_dump())


@app.post("/outils/demander_rappel", response_model=RappelReponse,
          dependencies=[Depends(verifier_jeton), Depends(verifier_outil_actif("demander_rappel"))])
def route_demander_rappel(requete: RappelRequete):
    return demander_rappel(**requete.model_dump())


@app.post("/outils/transferer_agent", response_model=TransfertReponse,
          dependencies=[Depends(verifier_jeton), Depends(verifier_outil_actif("transferer_agent"))])
def route_transferer_agent(requete: TransfertRequete):
    return transferer_agent(requete.motif, requete.resume)


@app.post("/outils/rechercher_information", response_model=InformationReponse,
          dependencies=[Depends(verifier_jeton), Depends(verifier_outil_actif("rechercher_information"))])
def route_rechercher_information(requete: InformationRequete):
    return rechercher_information(requete.question, requete.categorie)


# --- Back-office (Étape 6) ---

@app.post("/webhooks/elevenlabs/fin_appel", dependencies=[Depends(verifier_jeton_requete)])
async def route_webhook_fin_appel(request: Request):
    """Reçoit le webhook de fin d'appel d'ElevenLabs. URL à déclarer côté
    ElevenLabs avec le paramètre ?jeton=<API_TOKEN> à la fin.

    Format non vérifié contre la documentation officielle (bloquée
    depuis l'environnement où ce code a été écrit) : voir
    assistant/backoffice/appels.py pour le détail de cette réserve."""
    charge_brute = await request.json()
    enregistrer_appel(charge_brute)
    return JSONResponse({"recu": True})


@app.get("/backoffice/appels", response_class=HTMLResponse,
         dependencies=[Depends(verifier_acces_backoffice)])
def route_backoffice_liste_appels():
    return page_backoffice(
        lister_appels_avec_details(), lister_activations(), compter_appels(),
        resumer_evaluations(), resumer_tracabilite(),
    )


@app.post("/backoffice/appels/{appel_id}/evaluer",
          dependencies=[Depends(verifier_acces_backoffice)])
def route_backoffice_evaluer_appel(
    appel_id: int, qualite: Literal["bonne", "mauvaise"] = Form(...), note: str = Form("")
):
    enregistrer_evaluation(appel_id, qualite, note.strip() or None)
    return RedirectResponse(f"/backoffice/appels#appel-{appel_id}", status_code=303)


def _reponse_csv(contenu, nom_fichier):
    return Response(
        content=contenu,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{nom_fichier}"'},
    )


@app.get("/backoffice/exports/objets_perdus.csv", dependencies=[Depends(verifier_acces_backoffice)])
def route_export_objets_perdus():
    return _reponse_csv(exporter_objets_perdus(), "objets_perdus.csv")


@app.get("/backoffice/exports/demandes_rappel.csv", dependencies=[Depends(verifier_acces_backoffice)])
def route_export_demandes_rappel():
    return _reponse_csv(exporter_demandes_rappel(), "demandes_rappel.csv")


@app.get("/backoffice/exports/contacts_marketing.csv", dependencies=[Depends(verifier_acces_backoffice)])
def route_export_contacts_marketing():
    return _reponse_csv(exporter_contacts_marketing(), "contacts_marketing.csv")


@app.post("/backoffice/activation/{outil}/basculer",
          dependencies=[Depends(verifier_acces_backoffice)])
def route_backoffice_basculer(outil: str):
    basculer(outil)
    return RedirectResponse("/backoffice/appels", status_code=303)
