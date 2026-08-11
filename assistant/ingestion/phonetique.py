"""
Code phonétique simplifié pour le français.

But : réduire un nom d'arrêt à une forme qui ne dépend plus de son
orthographe exacte, pour que "Pinchinade" et "Les Pinchinades" (ou une
transcription vocale imparfaite) se retrouvent proches l'un de l'autre.

Ce n'est PAS un système linguistique rigoureux (type API/SAMPA) : c'est
un ensemble de règles pragmatiques sur les confusions les plus fréquentes
à l'oral en français. Première version, à ajuster avec de vraies
prononciations entendues au téléphone — voir CLAUDE.md, "le matching
phonétique est un cycle mesure-ajustement continu".
"""

import re
import unicodedata

# Groupes de lettres qu'on réduit à un même son, appliqués dans l'ordre
# (avant les règles à une seule lettre plus bas).
_GROUPES = [
    ("ch", "sh"),
    ("eau", "o"),
    ("aux", "o"),
    ("au", "o"),
    ("ain", "in"),
    ("ein", "in"),
    ("oin", "win"),
    ("an", "an"),
    ("en", "an"),
    ("am", "an"),
    ("em", "an"),
    ("on", "on"),
    ("om", "on"),
    ("ph", "f"),
    ("th", "t"),
    ("qu", "k"),
    ("ck", "k"),
    ("gu", "g"),
    ("ill", "y"),
    ("oi", "oa"),
    ("ou", "u"),
]

# Lettres isolées, appliquées après les groupes.
_LETTRES = {
    "y": "i",
    "w": "v",
    "ç": "s",
    "x": "ks",
    "ê": "e",
    "z": "s",
}


def _sans_accents(texte):
    forme = unicodedata.normalize("NFD", texte)
    return "".join(c for c in forme if unicodedata.category(c) != "Mn")


def code_phonetique(texte):
    """'Les Pinchinades' -> approximativement 'lepinsinad'."""
    t = _sans_accents(texte).lower()
    t = re.sub(r"[^a-z]+", "", t)  # espaces, apostrophes, tirets, chiffres : ignorés

    for motif, remplacement in _GROUPES:
        t = t.replace(motif, remplacement)
    for lettre, remplacement in _LETTRES.items():
        t = t.replace(lettre, remplacement)

    # c doux (devant e/i) -> s ; c dur -> k
    t = re.sub(r"c(?=[ei])", "s", t)
    t = t.replace("c", "k")
    # g doux (devant e/i) -> j
    t = re.sub(r"g(?=[ei])", "j", t)

    # consonnes finales muettes fréquentes (t, d, s, p, g final après une lettre)
    t = re.sub(r"[tdspg]$", "", t)

    # lettres doublées -> une seule
    t = re.sub(r"(.)\1+", r"\1", t)

    return t
