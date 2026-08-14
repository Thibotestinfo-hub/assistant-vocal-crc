"""
Évalue la qualité de recherche documentaire (assistant.outils.rechercher_information)
sur un jeu de questions réelles, avec la bonne page attendue.

Deux mesures affichées :
- Rappel top-5 : le bon fichier apparaît-il dans les 5 meilleurs blocs
  (chercher_blocs) ? C'est la mesure prévue par la méthode (Étape 4c).
- Réponse outil : ce que rechercher_information() renvoie réellement à
  l'agent (un seul résultat, avec seuils de confiance) est-il correct ?
  C'est la mesure qui compte pour l'appelant, plus stricte que le rappel
  top-5 puisqu'elle n'a droit qu'à une seule tentative.

Le jeu de questions vit dans tests/questions_evaluation.csv (colonnes
question ; categorie ; fichiers_attendus). fichiers_attendus vaut
"AUCUNE" pour les questions pièges, dont la réponse n'existe pas dans
le corpus : rechercher_information doit alors répondre trouve=False.

Usage : python3 -m assistant.evalcorpus
"""

import csv
import sys
import time
from pathlib import Path

from assistant.outils.rechercher_information import chercher_blocs, rechercher_information

QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "tests" / "questions_evaluation.csv"


def charger_questions():
    with open(QUESTIONS_PATH, encoding="utf-8") as f:
        lignes = list(csv.DictReader(f, delimiter=";"))
    for l in lignes:
        l["categorie"] = l["categorie"].strip() or None
        l["fichiers_attendus"] = [f.strip() for f in l["fichiers_attendus"].split(",")]
    return lignes


def evaluer(lignes):
    resultats = []
    for l in lignes:
        question = l["question"]
        categorie = l["categorie"]
        attendus = l["fichiers_attendus"]
        piege = attendus == ["AUCUNE"]

        top5 = chercher_blocs(question, categorie, n=5)
        fichiers_top5 = [bloc["fichier"] for _, bloc in top5]
        rappel_ok = True if piege else any(f in fichiers_top5 for f in attendus)

        debut = time.perf_counter()
        reponse = rechercher_information(question, categorie)
        duree_ms = (time.perf_counter() - debut) * 1000
        meilleur_score = top5[0][0] if top5 else None
        fichier_rendu = top5[0][1]["fichier"] if top5 else None
        if piege:
            outil_ok = not reponse["trouve"]
        else:
            # rechercher_information ne renvoie pas le champ "fichier" (pas dans le
            # contrat spec) : on le retrouve via le meilleur bloc de chercher_blocs.
            outil_ok = reponse["trouve"] and fichier_rendu in attendus

        resultats.append({
            "question": question,
            "piege": piege,
            "attendus": attendus,
            "rappel_ok": rappel_ok,
            "outil_ok": outil_ok,
            "fichiers_top5": fichiers_top5,
            "confiance": reponse.get("confiance"),
            "trouve": reponse["trouve"],
            "meilleur_score": meilleur_score,
            "duree_ms": duree_ms,
        })
    return resultats


def afficher(resultats):
    print(f"{len(resultats)} questions évaluées.\n")

    for r in resultats:
        marque = "OK  " if r["outil_ok"] else "FAIL"
        detail = "piège" if r["piege"] else "/".join(r["attendus"])
        rendu = r["confiance"] or ("rien" if not r["trouve"] else "?")
        score = f"{r['meilleur_score']:.3f}" if r["meilleur_score"] is not None else "  -  "
        print(f"[{marque}] ({rendu:6} {score}) {r['question']}")
        if not r["outil_ok"]:
            print(f"         attendu : {detail}")
            print(f"         top-5   : {r['fichiers_top5']}")

    n = len(resultats)
    n_rappel = sum(r["rappel_ok"] for r in resultats)
    n_outil = sum(r["outil_ok"] for r in resultats)

    print()
    print(f"Rappel top-5    : {n_rappel}/{n} ({100 * n_rappel / n:.0f} %)")
    print(f"Réponse outil   : {n_outil}/{n} ({100 * n_outil / n:.0f} %)  <- ce que l'appelant reçoit réellement")

    n_pieges = sum(r["piege"] for r in resultats)
    n_pieges_ok = sum(r["outil_ok"] for r in resultats if r["piege"])
    print(f"  dont questions pièges (doivent répondre 'je ne sais pas') : {n_pieges_ok}/{n_pieges}")

    # Le tout premier appel charge le modèle en mémoire (coût unique, pas
    # représentatif) : on regarde le régime de croisière à part, à
    # comparer au budget de 300 ms de CLAUDE.md.
    durees = sorted(r["duree_ms"] for r in resultats[1:])
    mediane = durees[len(durees) // 2]
    print(f"\nLatence rechercher_information (régime de croisière, 1er appel exclu) : "
          f"médiane {mediane:.0f} ms, max {max(durees):.0f} ms  (budget CLAUDE.md : 300 ms)")


def main():
    lignes = charger_questions()
    resultats = evaluer(lignes)
    afficher(resultats)
    n_outil = sum(r["outil_ok"] for r in resultats)
    sys.exit(0 if n_outil == len(resultats) else 1)


if __name__ == "__main__":
    main()
