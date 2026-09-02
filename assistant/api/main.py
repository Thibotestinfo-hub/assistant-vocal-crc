"""
API des outils de l'assistant vocal. Chaque endpoint /outils/* correspond
exactement à un outil décrit dans docs/spec-assistant-vocal-v0-revisee.md, §4.

Lancer en local : uv run uvicorn assistant.api.main:app --reload
"""

from typing import Literal
from urllib.parse import quote

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from assistant.api.auth import verifier_acces_backoffice, verifier_jeton, verifier_jeton_requete
from assistant.api.schemas import (
    HorairesRequete, HorairesReponse,
    InformationRequete, InformationReponse,
    ObjetPerduRequete, ObjetPerduReponse,
    RappelRequete, RappelReponse,
    RechercherArretRequete, RechercherArretReponse,
    SatisfactionRequete, SatisfactionReponse,
    TransfertRequete, TransfertReponse,
)
from assistant.backoffice.activation import (
    basculer, lister_activations, phrase_outils_actifs, verifier_outil_actif,
)
from assistant.backoffice.appels import (
    compter_appels, enregistrer_appel, enregistrer_evaluation, lister_appels_avec_details,
    resumer_evaluations, resumer_satisfaction_client, resumer_tracabilite, retraiter_tracabilite,
)
from assistant.backoffice.exports import (
    exporter_demandes_rappel, exporter_objets_perdus, lister_demandes_rappel,
)
from assistant.backoffice.page import page_backoffice
from assistant.backoffice.prononciation import ajouter_regle, lister_toutes_regles, supprimer_regle
from assistant.elevenlabs_api import apercu_voix, appels_en_cours, changer_reglages_voix
from assistant.outils.horaires_theoriques import horaires_theoriques
from assistant.outils.objets_perdus import enregistrer_objet_perdu
from assistant.outils.rappels import demander_rappel
from assistant.outils.rechercher_arret import rechercher_arret
from assistant.outils.rechercher_information import rechercher_information
from assistant.outils.satisfaction import enregistrer_satisfaction
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
        requete.heure_debut, requete.heure_fin,
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


@app.post("/outils/enregistrer_satisfaction", response_model=SatisfactionReponse,
          dependencies=[Depends(verifier_jeton)])
def route_enregistrer_satisfaction(requete: SatisfactionRequete):
    """Pas de verifier_outil_actif : ce n'est pas une fonctionnalité que
    l'équipe CRC activerait/désactiverait comme les autres outils, juste
    de l'instrumentation."""
    return enregistrer_satisfaction(requete.conversation_id, requete.satisfait)


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


@app.post("/webhooks/elevenlabs/personnalisation", dependencies=[Depends(verifier_jeton_requete)])
def route_webhook_personnalisation():
    """Appelé par ElevenLabs juste avant qu'une conversation démarre
    (Twilio/SIP/WhatsApp), en parallèle de la connexion téléphonique —
    donc sans latence perçue supplémentaire (documenté par ElevenLabs :
    "Twilio personalization"). Sert uniquement à fournir la variable
    dynamique {{outils_actifs}}, pour que le message d'accueil ne
    promette jamais une capacité coupée depuis le back-office (voir
    assistant/backoffice/activation.py, phrase_outils_actifs).

    Authentification par jeton en paramètre d'URL (?jeton=...), comme
    /webhooks/elevenlabs/fin_appel : constaté dans la configuration
    ElevenLabs (28/08) que ce type de webhook se déclare comme une entité
    réutilisable (URL + jeton dans l'URL), pas via un en-tête personnalisé
    — pas de "Security tab" avec en-tête distinct comme supposé au départ.

    On ignore volontairement le corps de la requête (caller_id,
    called_number, call_sid...) : on ne personnalise pas par appelant,
    seulement selon l'état d'activation global des outils."""
    return {"dynamic_variables": {"outils_actifs": phrase_outils_actifs()}}


@app.get("/backoffice/appels", response_class=HTMLResponse,
         dependencies=[Depends(verifier_acces_backoffice)])
def route_backoffice_liste_appels(erreur_voix: bool = False, detail_voix: str = "", erreur_prononciation: bool = False):
    try:
        en_cours = appels_en_cours()
    except Exception:
        # None : on ne sait pas (ElevenLabs indisponible/lent), à distinguer
        # d'une liste vide (on sait qu'il n'y a personne en ligne).
        en_cours = None
    return page_backoffice(
        lister_appels_avec_details(), lister_activations(), compter_appels(),
        resumer_evaluations(), resumer_satisfaction_client(), resumer_tracabilite(),
        lister_demandes_rappel(), en_cours, lister_toutes_regles(),
        erreur_voix=erreur_voix, detail_voix=detail_voix, erreur_prononciation=erreur_prononciation,
    )


@app.post("/backoffice/appels/retraiter-tracabilite",
          dependencies=[Depends(verifier_acces_backoffice)])
def route_backoffice_retraiter_tracabilite():
    retraiter_tracabilite()
    return RedirectResponse("/backoffice/appels#suivi", status_code=303)


@app.post("/backoffice/voix/changer",
          dependencies=[Depends(verifier_acces_backoffice)])
def route_backoffice_changer_voix(voice_id: str = Form(""), ton: str = Form(""), autre: str = Form("")):
    """Change la voix et/ou les réglages de ton (stability) et de style
    (autre) de l'agent ElevenLabs depuis le back-office, sans que
    l'équipe CRC ait besoin d'un compte ElevenLabs (voir
    assistant/elevenlabs_api.py). Champs vides : pas envoyés, donc pas
    modifiés (voir changer_reglages_voix). N'importe quelle panne côté
    ElevenLabs ne doit jamais faire planter le back-office : on redirige
    avec un indicateur d'erreur plutôt que de laisser l'exception
    remonter."""
    try:
        changer_reglages_voix(
            voice_id=voice_id or None,
            stability=float(ton) if ton else None,
            style=float(autre) if autre else None,
        )
    except Exception as erreur:
        # Message affiché directement dans le back-office plutôt que
        # seulement loggé côté serveur (onglet Logs de Clever Cloud) :
        # constaté en usage réel que cet onglet peut rester vide sans
        # explication, donc ne pas en dépendre pour diagnostiquer.
        print(f"changer_reglages_voix a échoué : {erreur!r}", flush=True)
        detail = quote(str(erreur)[:300])
        return RedirectResponse(f"/backoffice/appels?erreur_voix=1&detail_voix={detail}", status_code=303)
    return RedirectResponse("/backoffice/appels", status_code=303)


@app.get("/backoffice/voix/{voice_id}/apercu",
         dependencies=[Depends(verifier_acces_backoffice)])
def route_backoffice_apercu_voix(voice_id: str):
    """Redirige vers un échantillon audio de la voix, demandé à
    ElevenLabs à chaque clic (jamais stocké — voir apercu_voix, certaines
    URLs sont probablement à durée de vie limitée). Statut 502 si
    ElevenLabs est indisponible : le <audio> du navigateur échoue
    silencieusement plutôt que de faire planter le back-office. L'erreur
    est quand même loggée côté serveur (onglet Logs de Clever Cloud) —
    un <audio> qui échoue en silence ne doit pas nous laisser sans piste
    pour diagnostiquer."""
    try:
        url = apercu_voix(voice_id)
    except Exception as erreur:
        print(f"apercu_voix({voice_id!r}) a échoué : {erreur!r}", flush=True)
        return Response(content=str(erreur)[:300], status_code=502, media_type="text/plain")
    if not url:
        print(f"apercu_voix({voice_id!r}) : pas de preview_url renvoyé par ElevenLabs", flush=True)
        return Response(
            content="ElevenLabs n'a renvoyé aucun aperçu pour cette voix",
            status_code=404, media_type="text/plain",
        )
    return RedirectResponse(url, status_code=302)


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


@app.post("/backoffice/activation/{outil}/basculer",
          dependencies=[Depends(verifier_acces_backoffice)])
def route_backoffice_basculer(outil: str):
    basculer(outil)
    return RedirectResponse("/backoffice/appels", status_code=303)


@app.post("/backoffice/prononciation/ajouter",
          dependencies=[Depends(verifier_acces_backoffice)])
def route_backoffice_ajouter_prononciation(grapheme: str = Form(...), alias: str = Form(...)):
    resultat = ajouter_regle(grapheme, alias)
    if not resultat["succes"]:
        return RedirectResponse("/backoffice/appels?erreur_prononciation=1#prononciation", status_code=303)
    return RedirectResponse("/backoffice/appels#prononciation", status_code=303)


@app.post("/backoffice/prononciation/{grapheme}/supprimer",
          dependencies=[Depends(verifier_acces_backoffice)])
def route_backoffice_supprimer_prononciation(grapheme: str):
    supprimer_regle(grapheme)
    return RedirectResponse("/backoffice/appels#prononciation", status_code=303)
