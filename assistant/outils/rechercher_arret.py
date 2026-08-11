"""
Outil `rechercher_arret` — identifie un arrêt à partir de ce que dit
l'appelant. Contrat exact : docs/spec-assistant-vocal-v0-revisee.md, §4.
"""

import unicodedata

from rapidfuzz import fuzz

from assistant.outils.arrets import charger_arrets_logiques
from assistant.ingestion.phonetique import code_phonetique

NB_CANDIDATS_MAX = 4
SEUIL_HAUTE = 0.85
ECART_HAUTE = 0.15
SEUIL_BASSE = 0.55


def _normaliser(texte):
    forme = unicodedata.normalize("NFD", texte)
    sans_accents = "".join(c for c in forme if unicodedata.category(c) != "Mn")
    return sans_accents.lower().strip()


def rechercher_arret(texte, commune=None, ligne=None, conn=None):
    candidats = charger_arrets_logiques(conn)

    if commune:
        commune_norm = _normaliser(commune)
        candidats = [c for c in candidats if _normaliser(c["commune"]) == commune_norm]
    if ligne:
        candidats = [c for c in candidats if ligne in c["lignes"]]

    requete_normalisee = _normaliser(texte)
    requete_phonetique = code_phonetique(texte)

    scores = []
    for c in candidats:
        score_texte = fuzz.token_sort_ratio(requete_normalisee, c["texte_normalise"])
        score_phonetique = fuzz.ratio(requete_phonetique, c["phonetique"])
        score = max(score_texte, score_phonetique) / 100
        scores.append((score, c))

    scores.sort(key=lambda x: x[0], reverse=True)
    meilleurs = scores[:NB_CANDIDATS_MAX]

    if not meilleurs or meilleurs[0][0] <= SEUIL_BASSE:
        confiance = "basse"
    elif (meilleurs[0][0] > SEUIL_HAUTE
          and (len(meilleurs) == 1 or meilleurs[0][0] - meilleurs[1][0] > ECART_HAUTE)):
        confiance = "haute"
    else:
        confiance = "moyenne"

    return {
        "confiance": confiance,
        "candidats": [
            {
                "arret_id": c["stop_id"],
                "nom": c["stop_name"],
                "commune": c["commune"],
                "lignes": c["lignes"],
                "score": round(score, 2),
            }
            for score, c in meilleurs
        ],
    }
