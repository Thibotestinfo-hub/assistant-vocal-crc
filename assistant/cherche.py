"""
Recherche d'arrêt par nom approximatif ou prononciation approchée.

Combine deux signaux :
- le code phonétique (assistant.ingestion.phonetique), qui absorbe les
  confusions de prononciation ("ph"/"f", consonnes finales muettes...) ;
- une distance d'édition classique sur le texte normalisé, qui absorbe
  les fautes de frappe et les mots dans un ordre différent.

Le meilleur des deux scores l'emporte pour chaque candidat : si l'un des
deux signaux dit "ça ressemble beaucoup", c'est suffisant.

Usage : python3 -m assistant.cherche "pinchinade"
        (uv run python -m assistant.cherche "pinchinade")
"""

import sqlite3
import sys
import unicodedata
from pathlib import Path

from rapidfuzz import fuzz

from assistant.ingestion.phonetique import code_phonetique

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "gtfs.db"

NB_RESULTATS = 5


def _normaliser(texte):
    forme = unicodedata.normalize("NFD", texte)
    sans_accents = "".join(c for c in forme if unicodedata.category(c) != "Mn")
    return sans_accents.lower().strip()


def charger_candidats(conn):
    """Un candidat par (stop_name, commune) distinct, avec un stop_id
    représentatif (pour l'instant juste le premier rencontré)."""
    lignes = conn.execute(
        "SELECT stop_id, stop_name, commune FROM stops WHERE location_type = 0"
    ).fetchall()

    candidats = {}
    for stop_id, stop_name, commune in lignes:
        cle = (stop_name, commune)
        if cle not in candidats:
            candidats[cle] = {
                "stop_id": stop_id,
                "stop_name": stop_name,
                "commune": commune,
                "texte_normalise": _normaliser(stop_name),
                "phonetique": code_phonetique(stop_name),
                "n_quais": 0,
            }
        candidats[cle]["n_quais"] += 1
    return list(candidats.values())


def chercher(requete, candidats, n=NB_RESULTATS):
    requete_normalisee = _normaliser(requete)
    requete_phonetique = code_phonetique(requete)

    resultats = []
    for c in candidats:
        score_texte = fuzz.token_sort_ratio(requete_normalisee, c["texte_normalise"])
        score_phonetique = fuzz.ratio(requete_phonetique, c["phonetique"])
        score = max(score_texte, score_phonetique)
        resultats.append((score, score_texte, score_phonetique, c))

    resultats.sort(key=lambda r: r[0], reverse=True)
    return resultats[:n]


def main():
    if len(sys.argv) < 2:
        print("Usage : python -m assistant.cherche \"<ce que dit l'appelant>\"")
        sys.exit(1)

    requete = " ".join(sys.argv[1:])
    conn = sqlite3.connect(DB_PATH)
    candidats = charger_candidats(conn)
    conn.close()

    resultats = chercher(requete, candidats)

    print(f"Recherche : {requete!r}\n")
    for score, score_texte, score_phonetique, c in resultats:
        quais = f" ({c['n_quais']} quais)" if c["n_quais"] > 1 else ""
        print(f"  {score:5.1f}  {c['stop_name']}{quais} — {c['commune']}  "
              f"[texte={score_texte:.0f} phonétique={score_phonetique:.0f}]")


if __name__ == "__main__":
    main()
