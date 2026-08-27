"""
Dictionnaire de prononciation (data/prononciation.pls) chargé côté
application, pas seulement envoyé à ElevenLabs.

Jusqu'ici, la correction de prononciation des noms d'arrêts abrégés
("Collège F. Léger", "GS P. Picasso"...) reposait entièrement sur la
correspondance faite par ElevenLabs à partir de ce même fichier. Repéré
peu fiable en test vocal (26/08/2026) : "Collège F. Léger" reste mal
prononcé malgré une règle présente, byte à byte identique au nom GTFS
(vérifié). Hypothèse retenue : les abréviations contenant un point
("F.", "E.", "J.-J"...) cassent la correspondance côté ElevenLabs —
18 des 323 règles du dictionnaire sont dans ce cas.

Plutôt que de dépendre uniquement de ce mécanisme, ce module applique la
même table de correspondance nous-mêmes, côté outils (voir
assistant/outils/arrets.py), avant de renvoyer un nom d'arrêt à l'agent :
le nom prononcé à l'appelant est alors déjà en toutes lettres, sans
attendre qu'ElevenLabs le corrige. Le fichier .pls reste la seule source
de vérité (une seule liste à tenir à jour), simplement lu deux fois : une
fois par ElevenLabs (dictionnaire de prononciation), une fois par nous.

Usage de vérification : python3 -m assistant.ingestion.prononciation
"""

from pathlib import Path
from xml.etree import ElementTree as ET

RACINE = Path(__file__).resolve().parent.parent.parent
PLS_PATH = RACINE / "data" / "prononciation.pls"
_NS = "{http://www.w3.org/2005/01/pronunciation-lexicon}"


def _charger_dictionnaire():
    arbre = ET.parse(PLS_PATH)
    dictionnaire = {}
    for lexeme in arbre.getroot().findall(f"{_NS}lexeme"):
        grapheme = lexeme.findtext(f"{_NS}grapheme")
        alias = lexeme.findtext(f"{_NS}alias")
        if grapheme and alias:
            dictionnaire[grapheme] = alias
    return dictionnaire


_DICTIONNAIRE = _charger_dictionnaire()


def nom_prononcable(nom):
    """Version du nom à faire prononcer par la voix : la forme développée
    si une règle existe pour ce nom exact (correspondance stricte, comme
    dans le GTFS), sinon le nom tel quel — jamais d'approximation."""
    return _DICTIONNAIRE.get(nom, nom)


if __name__ == "__main__":
    print(f"{len(_DICTIONNAIRE)} règles chargées depuis {PLS_PATH}")
    avec_point = {g: a for g, a in _DICTIONNAIRE.items() if "." in g}
    print(f"{len(avec_point)} contiennent un point dans le nom abrégé :")
    for grapheme, alias in avec_point.items():
        print(f"  {grapheme!r} -> {alias!r}")
