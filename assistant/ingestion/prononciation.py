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
attendre qu'ElevenLabs le corrige. Le fichier .pls reste la source de
vérité "de référence" (relue systématiquement par l'équipe), complétée
par des règles ajoutées depuis le back-office (table
regles_prononciation, dans data/etat/assistant.db — voir
assistant/backoffice/prononciation.py) : contrairement au fichier .pls,
remis à neuf à chaque déploiement (comme tout data/ hors data/etat/),
ces règles-là survivent aux déploiements. Une règle du back-office
l'emporte sur celle du fichier pour un même nom.

Usage de vérification : python3 -m assistant.ingestion.prononciation
"""

from pathlib import Path
from xml.etree import ElementTree as ET

from assistant.outils.db import connexion_app

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


def dictionnaire_fichier():
    """Copie du dictionnaire chargé depuis data/prononciation.pls — pour
    affichage (voir assistant/backoffice/prononciation.py), jamais pour
    modification (le fichier est versionné, pas éditable depuis l'app)."""
    return dict(_DICTIONNAIRE)


def regles_backoffice():
    """Règles ajoutées depuis le back-office (persistantes, voir
    l'en-tête du module). Une seule requête par appelant, jamais une par
    arrêt (voir assistant/outils/arrets.py) — sinon le budget de 300 ms
    de l'API ne tiendrait pas sur les listes de plusieurs centaines
    d'arrêts."""
    conn = connexion_app()
    lignes = conn.execute("SELECT grapheme, alias FROM regles_prononciation").fetchall()
    conn.close()
    return {r["grapheme"]: r["alias"] for r in lignes}


def nom_prononcable(nom, overrides=None):
    """Version du nom à faire prononcer par la voix : la forme développée
    si une règle existe pour ce nom exact (correspondance stricte, comme
    dans le GTFS), sinon le nom tel quel — jamais d'approximation.
    overrides : résultat de regles_backoffice(), à passer explicitement
    pour éviter une requête par arrêt (voir plus haut) ; si omis, cette
    fonction interroge elle-même la base (pratique en usage isolé,
    ex. python3 -m assistant.ingestion.prononciation)."""
    if overrides is None:
        overrides = regles_backoffice()
    if nom in overrides:
        return overrides[nom]
    return _DICTIONNAIRE.get(nom, nom)


if __name__ == "__main__":
    print(f"{len(_DICTIONNAIRE)} règles chargées depuis {PLS_PATH}")
    avec_point = {g: a for g, a in _DICTIONNAIRE.items() if "." in g}
    print(f"{len(avec_point)} contiennent un point dans le nom abrégé :")
    for grapheme, alias in avec_point.items():
        print(f"  {grapheme!r} -> {alias!r}")
