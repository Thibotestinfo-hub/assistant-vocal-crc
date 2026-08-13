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
BUDGET_MS = 300

en_tete = {"Authorization": f"Bearer {TOKEN}"}


def appeler(methode, chemin, **kwargs):
    debut = time.perf_counter()
    reponse = httpx.request(methode, f"{URL_BASE}{chemin}", timeout=10, follow_redirects=True, **kwargs)
    duree_ms = (time.perf_counter() - debut) * 1000
    return reponse, duree_ms


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

    print()
    n_ok = sum(resultats)
    print(f"{n_ok}/{len(resultats)} vérifications passées.")
    sys.exit(0 if n_ok == len(resultats) else 1)


if __name__ == "__main__":
    main()
