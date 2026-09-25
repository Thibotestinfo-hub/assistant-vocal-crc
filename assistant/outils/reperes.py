"""
Repères connus (mairies, etc.) — permet à calculer_itineraire de résoudre
une destination dite en clair ("la mairie de Vitrolles") vers l'arrêt le
plus proche, sans dépendre d'un service de géocodage externe. Voir
data/reperes.yaml pour le détail et la méthode de collecte.

C'est un outil expérimental (voir docs/prochaines-etapes.md) : liste de
repères volontairement réduite pour commencer (une seule par commune),
désactivé par défaut dans le back-office.
"""

import math
import unicodedata
from pathlib import Path

import yaml

from assistant.outils.arrets import charger_arrets_logiques

RACINE = Path(__file__).resolve().parent.parent.parent
REPERES_PATH = RACINE / "data" / "reperes.yaml"

RAYON_TERRE_KM = 6371


def _normaliser(texte):
    forme = unicodedata.normalize("NFD", texte or "")
    sans_accents = "".join(c for c in forme if unicodedata.category(c) != "Mn")
    return sans_accents.lower().strip()


def _charger_reperes():
    return yaml.safe_load(REPERES_PATH.read_text(encoding="utf-8")) or []


def trouver_reperes(texte, commune=None):
    """Repères dont le libellé apparaît dans `texte` (ex. "mairie" trouvé
    dans "je voudrais aller à la mairie"). Si `commune` est fourni, ne
    garde que les repères de cette commune — sinon, plusieurs communes
    peuvent matcher (ambiguïté à lever par l'agent, même logique que les
    arrêts homonymes)."""
    texte_normalise = _normaliser(texte)
    commune_normalisee = _normaliser(commune) if commune else None
    candidats = []
    for repere in _charger_reperes():
        if _normaliser(repere["libelle"]) not in texte_normalise:
            continue
        if commune_normalisee and _normaliser(repere["commune"]) != commune_normalisee:
            continue
        candidats.append(repere)
    return candidats


def _distance_km(lat1, lon1, lat2, lon2):
    """Distance à vol d'oiseau (formule de haversine) — suffisant pour
    trouver l'arrêt le plus proche d'un repère, pas pour calculer un
    vrai trajet piéton (voirie, obstacles)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * RAYON_TERRE_KM * math.asin(math.sqrt(a))


def arret_le_plus_proche(lat, lon, conn=None):
    """L'arrêt logique (voir assistant.outils.arrets) le plus proche
    d'une coordonnée donnée, à vol d'oiseau, avec sa distance en km."""
    arrets = charger_arrets_logiques(conn)
    if not arrets:
        return None, None
    meilleur = min(arrets, key=lambda a: _distance_km(lat, lon, a["lat"], a["lon"]))
    distance = _distance_km(lat, lon, meilleur["lat"], meilleur["lon"])
    return meilleur, distance


def rechercher_repere(texte, commune=None, conn=None):
    """Outil exposé à l'agent : résout un repère cité par l'appelant
    ("la mairie") vers l'arrêt le plus proche. Renvoie une liste (jamais
    un seul résultat imposé) : sans commune précisée, plusieurs communes
    peuvent matcher — à l'agent de lever l'ambiguïté, même logique que
    rechercher_arret avec les arrêts homonymes."""
    candidats = []
    for repere in trouver_reperes(texte, commune):
        arret, distance = arret_le_plus_proche(repere["lat"], repere["lon"], conn)
        if arret is None:
            continue
        candidats.append({
            "commune": repere["commune"],
            "libelle": repere["libelle"],
            "arret_id": arret["stop_id"],
            "arret_nom": arret["nom_prononcable"],
            "distance_km": round(distance, 2),
        })
    return {"candidats": candidats}
