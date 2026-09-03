"""
Script de vérification du back-office (Étape 6) : webhook de fin
d'appel, pages protégées, exports CSV, activation des outils — contre
une API déjà déployée, pas seulement testée en local.

L'API doit déjà tourner : uv run python run.py

Usage : uv run python tests/verifier_backoffice.py [URL_BASE]
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

en_tete = {"Authorization": f"Bearer {TOKEN}"}
auth_backoffice = ("crc", TOKEN)


def appeler(methode, chemin, **kwargs):
    debut = time.perf_counter()
    reponse = httpx.request(methode, f"{URL_BASE}{chemin}", timeout=10, follow_redirects=True, **kwargs)
    duree_ms = (time.perf_counter() - debut) * 1000
    return reponse, duree_ms


def verifier(nom, ok, reponse, duree_ms, detail=""):
    marque = "OK  " if ok else "FAIL"
    print(f"[{marque}] {nom:40} {duree_ms:6.1f} ms  (statut {reponse.status_code})")
    if not ok:
        print(f"       {detail or reponse.text[:200]}")
    return ok


def main():
    resultats = []
    conversation_test = f"test_verif_{int(time.time())}"

    # --- Webhook de fin d'appel ---

    r, d = appeler("POST", "/webhooks/elevenlabs/fin_appel",
                    json={"conversation_id": conversation_test})
    ok = r.status_code == 401
    resultats.append(verifier("POST webhook sans jeton -> 401", ok, r, d))

    r, d = appeler("POST", f"/webhooks/elevenlabs/fin_appel?jeton={TOKEN}",
                    json={"conversation_id": conversation_test, "status": "test"})
    ok = r.status_code == 200
    resultats.append(verifier("POST webhook avec jeton", ok, r, d))

    # --- Pages protégées ---

    r, d = appeler("GET", "/backoffice/appels")
    ok = r.status_code == 401
    resultats.append(verifier("GET /backoffice/appels sans auth -> 401", ok, r, d))

    r, d = appeler("GET", "/backoffice/appels", auth=auth_backoffice)
    ok = r.status_code == 200 and conversation_test in r.text
    resultats.append(verifier(
        "GET /backoffice/appels (voit le test)", ok, r, d,
        "l'appel de test n'apparaît pas dans la liste" if r.status_code == 200 else "",
    ))

    ok = r.status_code == 200 and "Outils actifs" in r.text
    resultats.append(verifier("GET /backoffice/appels (panneau activation présent)", ok, r, d))

    # --- Exports CSV ---

    r, d = appeler("GET", "/backoffice/exports/objets_perdus.csv")
    resultats.append(verifier("GET export objets_perdus sans auth -> 401", r.status_code == 401, r, d))

    r, d = appeler("GET", "/backoffice/exports/objets_perdus.csv", auth=auth_backoffice)
    ok = r.status_code == 200 and r.headers.get("content-type", "").startswith("text/csv")
    resultats.append(verifier("GET export objets_perdus.csv", ok, r, d))

    r, d = appeler("GET", "/backoffice/exports/demandes_rappel.csv", auth=auth_backoffice)
    ok = r.status_code == 200 and r.headers.get("content-type", "").startswith("text/csv")
    resultats.append(verifier("GET export demandes_rappel.csv", ok, r, d))

    # --- Activation des outils ---
    # enregistrer_objet_perdu : choisi parce qu'une brève désactivation
    # pendant ce script n'a aucune conséquence dangereuse. Depuis le
    # 03/09/2026, demander_rappel et transferer_agent ne sont plus
    # désactivables du tout (ce sont les deux seules portes de sortie vers
    # un humain), donc plus utilisables pour ce test. Le bloc finally
    # garantit la réactivation même si une vérification échoue en cours
    # de route, pour ne jamais laisser l'assistant en production avec un
    # outil coupé par erreur.
    objet_perdu_payload = {
        "nature": "test", "description": "vérification back-office",
        "date_perte": "2026-01-01", "creneau_horaire": "matin", "lieu": "incertain",
        "nom": "test", "telephone": "0600000000", "opt_in_marketing": False,
    }
    try:
        r, d = appeler("POST", "/backoffice/activation/enregistrer_objet_perdu/basculer", auth=auth_backoffice)
        resultats.append(verifier("POST bascule enregistrer_objet_perdu (désactive)", r.status_code == 200, r, d))

        r, d = appeler("POST", "/outils/enregistrer_objet_perdu", headers=en_tete, json=objet_perdu_payload)
        ok = r.status_code == 503
        resultats.append(verifier("POST outil désactivé -> 503", ok, r, d))
    finally:
        r, d = appeler("POST", "/backoffice/activation/enregistrer_objet_perdu/basculer", auth=auth_backoffice)
        reactive = verifier("POST bascule enregistrer_objet_perdu (réactive)", r.status_code == 200, r, d)
        resultats.append(reactive)
        if not reactive:
            print("       ⚠️  ATTENTION : enregistrer_objet_perdu pourrait être resté désactivé, à vérifier à la main sur /backoffice/appels")

    r, d = appeler("POST", "/outils/enregistrer_objet_perdu", headers=en_tete, json=objet_perdu_payload)
    resultats.append(verifier("POST outil réactivé -> fonctionne", r.status_code == 200, r, d))

    print()
    n_ok = sum(resultats)
    print(f"{n_ok}/{len(resultats)} vérifications passées.")
    sys.exit(0 if n_ok == len(resultats) else 1)


if __name__ == "__main__":
    main()
