"""
Script de vérification de l'API : appelle chaque endpoint, vérifie le
format de la réponse et mesure le temps de réponse (budget : 300 ms,
voir CLAUDE.md).

L'API doit déjà tourner : uv run python run.py

Usage : uv run python tests/verifier_api.py [URL_BASE]
        (URL_BASE par défaut : http://127.0.0.1:9000)
"""

import os
import sys
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

URL_BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:9000"
TOKEN = os.environ["API_TOKEN"]
MOT_DE_PASSE_BACKOFFICE = os.environ["BACKOFFICE_MOT_DE_PASSE"]
BUDGET_MS = 300

en_tete = {"Authorization": f"Bearer {TOKEN}"}
auth_backoffice = ("crc", MOT_DE_PASSE_BACKOFFICE)


def appeler(methode, chemin, **kwargs):
    debut = time.perf_counter()
    reponse = httpx.request(methode, f"{URL_BASE}{chemin}", timeout=10, follow_redirects=True, **kwargs)
    duree_ms = (time.perf_counter() - debut) * 1000
    return reponse, duree_ms


def verifier_statut(nom, reponse, duree_ms, statut_attendu=200):
    """Variante de verifier() pour les routes qui ne renvoient pas de JSON
    à vérifier (ex. bascule d'activation, simple redirection)."""
    ok = reponse.status_code == statut_attendu
    marque = "OK " if ok else "FAIL"
    print(f"[{marque}] {nom:30} {duree_ms:6.1f} ms  (statut {reponse.status_code})")
    return ok


def verifier(nom, reponse, duree_ms, cles_attendues):
    dans_budget = duree_ms <= BUDGET_MS
    statut_ok = reponse.status_code == 200
    corps = reponse.json() if statut_ok else {}
    cles_ok = statut_ok and all(cle in corps for cle in cles_attendues)

    ok = dans_budget and statut_ok and cles_ok
    marque = "OK " if ok else "FAIL"
    print(f"[{marque}] {nom:30} {duree_ms:6.1f} ms  (statut {reponse.status_code})")
    if not statut_ok:
        print(f"       réponse : {reponse.text[:200]}")
    elif not cles_ok:
        print(f"       clés manquantes, attendu {cles_attendues}, reçu {list(corps.keys())}")
    if not dans_budget:
        print(f"       ⚠️  dépasse le budget de {BUDGET_MS} ms")
    return ok


def main():
    resultats = []

    # Sans authentification : /sante doit rester accessible.
    r, d = appeler("GET", "/sante")
    resultats.append(verifier("GET /sante", r, d, ["statut"]))

    # Sans jeton : les outils doivent refuser (401).
    r, d = appeler("POST", "/outils/rechercher_arret", json={"texte": "pinchinade"})
    ok_401 = r.status_code == 401
    print(f"[{'OK  ' if ok_401 else 'FAIL'}] {'POST sans jeton -> 401':30} {d:6.1f} ms  (statut {r.status_code})")
    resultats.append(ok_401)

    r, d = appeler("POST", "/outils/rechercher_arret", headers=en_tete,
                    json={"texte": "pinchinade"})
    resultats.append(verifier("POST /outils/rechercher_arret", r, d, ["confiance", "candidats"]))
    arret_id = r.json()["candidats"][0]["arret_id"] if r.status_code == 200 else "BDE-24978"

    r, d = appeler("POST", "/outils/horaires_theoriques", headers=en_tete,
                    json={"arret_id": arret_id, "type": "prochains"})
    resultats.append(verifier("POST /outils/horaires_theoriques", r, d,
                               ["type_service", "circule_aujourdhui", "departs", "premier", "dernier"]))

    r, d = appeler("POST", "/outils/rechercher_information", headers=en_tete,
                    json={"question": "c'est combien un carnet de tickets"})
    resultats.append(verifier("POST /outils/rechercher_information", r, d, ["trouve"]))

    r, d = appeler("POST", "/outils/enregistrer_objet_perdu", headers=en_tete, json={
        "nature": "sac", "description": "sac à dos gris, test automatique",
        "date_perte": "2026-08-11", "creneau_horaire": "vers 9h",
        "lieu": "arret", "nom": "Test Script", "telephone": "0600000000",
        "opt_in_marketing": False,
    })
    resultats.append(verifier("POST /outils/enregistrer_objet_perdu", r, d, ["succes"]))

    r, d = appeler("POST", "/outils/demander_rappel", headers=en_tete, json={
        "telephone": "0600000000", "motif": "reclamation",
        "resume": "Test automatique du script de vérification",
    })
    resultats.append(verifier("POST /outils/demander_rappel", r, d, ["succes"]))

    r, d = appeler("POST", "/outils/transferer_agent", headers=en_tete, json={
        "motif": "test", "resume": "Test automatique",
    })
    resultats.append(verifier("POST /outils/transferer_agent", r, d, ["succes", "transfert_id"]))

    r, d = appeler("POST", "/outils/enregistrer_satisfaction", headers=en_tete, json={
        "conversation_id": "test-script", "satisfait": True,
    })
    resultats.append(verifier("POST /outils/enregistrer_satisfaction", r, d, ["succes"]))

    # calculer_itineraire et rechercher_repere sont désactivés par défaut
    # (même interrupteur, voir CLAUDE.md et assistant/outils/db.py) : on
    # les active le temps du test, puis on restaure l'état par défaut
    # dans tous les cas, pour ne jamais laisser l'assistant en production
    # avec une fonctionnalité expérimentale allumée par erreur.
    try:
        r, d = appeler("POST", "/backoffice/activation/calculer_itineraire/basculer", auth=auth_backoffice)
        resultats.append(verifier_statut("POST bascule calculer_itineraire (active)", r, d))

        r, d = appeler("POST", "/outils/rechercher_repere", headers=en_tete,
                        json={"texte": "mairie"})
        resultats.append(verifier("POST /outils/rechercher_repere", r, d, ["candidats"]))

        r, d = appeler("POST", "/outils/calculer_itineraire", headers=en_tete,
                        json={"arret_depart_id": arret_id, "arret_arrivee_id": arret_id})
        resultats.append(verifier("POST /outils/calculer_itineraire", r, d, ["trouve"]))
    finally:
        r, d = appeler("POST", "/backoffice/activation/calculer_itineraire/basculer", auth=auth_backoffice)
        reactive = verifier_statut("POST bascule calculer_itineraire (restaure désactivé)", r, d)
        resultats.append(reactive)
        if not reactive:
            print("       ⚠️  ATTENTION : calculer_itineraire/rechercher_repere pourraient être restés actifs, à vérifier à la main sur /backoffice/appels")

    # calculer_itineraire_complexe : désactivé par défaut, dépend de
    # GOOGLE_ROUTES_API_KEY (absente dans cet environnement de test —
    # échec sandbox connu, voir docs/prochaines-etapes.md). On vérifie la
    # forme de la réponse (trouve=false avec une erreur explicite), pas
    # un vrai calcul Google Routes.
    try:
        r, d = appeler("POST", "/backoffice/activation/calculer_itineraire_complexe/basculer", auth=auth_backoffice)
        resultats.append(verifier_statut("POST bascule calculer_itineraire_complexe (active)", r, d))

        r, d = appeler("POST", "/outils/calculer_itineraire_complexe", headers=en_tete,
                        json={"arret_depart_id": arret_id, "arret_arrivee_id": arret_id})
        resultats.append(verifier("POST /outils/calculer_itineraire_complexe", r, d, ["trouve"]))
    finally:
        r, d = appeler("POST", "/backoffice/activation/calculer_itineraire_complexe/basculer", auth=auth_backoffice)
        reactive = verifier_statut("POST bascule calculer_itineraire_complexe (restaure désactivé)", r, d)
        resultats.append(reactive)
        if not reactive:
            print("       ⚠️  ATTENTION : calculer_itineraire_complexe pourrait être resté actif, à vérifier à la main sur /backoffice/appels")

    # envoyer_sms_itineraire : désactivé par défaut. La route répond tout
    # de suite (accepte=true) avant même de tenter l'envoi réel, qui se
    # fait en tâche de fond (voir assistant/api/main.py) — donc ce test
    # vérifie que la route accepte la demande et respecte le budget de
    # latence, pas que le SMS part réellement. TWILIO_ACCOUNT_SID/
    # TWILIO_AUTH_TOKEN sont absents dans cet environnement de test
    # (échec sandbox connu) : la tâche de fond échouera silencieusement,
    # visible seulement dans sms_envoyes, pas dans cette réponse.
    try:
        r, d = appeler("POST", "/backoffice/activation/envoyer_sms_itineraire/basculer", auth=auth_backoffice)
        resultats.append(verifier_statut("POST bascule envoyer_sms_itineraire (active)", r, d))

        r, d = appeler("POST", "/outils/envoyer_sms_itineraire", headers=en_tete, json={
            "telephone": "0600000000", "arret_depart_id": arret_id, "arret_arrivee_id": arret_id,
        })
        resultats.append(verifier("POST /outils/envoyer_sms_itineraire", r, d, ["accepte"]))
    finally:
        r, d = appeler("POST", "/backoffice/activation/envoyer_sms_itineraire/basculer", auth=auth_backoffice)
        reactive = verifier_statut("POST bascule envoyer_sms_itineraire (restaure désactivé)", r, d)
        resultats.append(reactive)
        if not reactive:
            print("       ⚠️  ATTENTION : envoyer_sms_itineraire pourrait être resté actif, à vérifier à la main sur /backoffice/appels")

    print()
    n_ok = sum(resultats)
    print(f"{n_ok}/{len(resultats)} vérifications passées.")
    sys.exit(0 if n_ok == len(resultats) else 1)


if __name__ == "__main__":
    main()
