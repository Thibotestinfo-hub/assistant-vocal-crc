"""
Outil `calculer_itineraire_complexe` — expérimental, désactivé par défaut.
Contrat : docs/spec-assistant-vocal-v0-revisee.md, §4.

Décision de conception (voir docs/prochaines-etapes.md, 08/10/2026) :
`calculer_itineraire` (assistant/outils/itineraire.py) reste le seul
calculateur utilisé pour les trajets simples qu'il sait couvrir (direct
ou une correspondance, sans marche, directement depuis le GTFS). Ce
module n'est appelé qu'en repli, quand celui-ci renvoie trouve=False —
jamais les deux pour le même trajet, pour ne jamais risquer deux
réponses différentes sur un même trajet (risque identifié explicitement
par l'utilisateur).

S'appuie sur l'API Google Routes (travelMode=TRANSIT), qui couvre la
marche et plusieurs correspondances — au prix d'un appel réseau externe.
Latence réelle mesurée (08/10/2026, depuis Cloud Shell, donc optimiste) :
~170 ms, déjà plus de la moitié du budget de 300 ms de CLAUDE.md — c'est
pourquoi cet outil est volontairement tenu à l'écart du calculateur
principal plutôt que d'être une tentative systématique en tête.

Nécessite GOOGLE_ROUTES_API_KEY dans l'environnement — absente, l'outil
répond simplement trouve=False (dégradation gracieuse, pas d'erreur 500 :
un réseau dupliqué sans cette clé doit continuer à fonctionner, voir
CLAUDE.md sur le paramétrage).
"""

import os
from datetime import datetime, timedelta, timezone

import httpx

from assistant.outils.arrets import charger_arrets_logiques
from assistant.outils.db import connexion_gtfs
from assistant.outils.horaires_theoriques import FUSEAU

BASE_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

# Généreux par rapport au budget de 300 ms de CLAUDE.md, assumé pour ce
# repli explicitement hors chemin critique habituel (voir docstring du
# module) — à resserrer une fois une vraie mesure faite depuis Clever
# Cloud (pas seulement Cloud Shell).
TIMEOUT_SECONDES = 4.0

FIELD_MASK = (
    "routes.duration,"
    "routes.legs.steps.travelMode,"
    "routes.legs.steps.transitDetails"
)


def _en_tete(cle):
    return {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": cle,
        "X-Goog-FieldMask": FIELD_MASK,
    }


def _departure_time_rfc3339(date, heure):
    """Google exige departureTime (ou arrivalTime) pour un calcul TRANSIT.
    +30s par défaut quand ni date ni heure ne sont précisées, pour ne
    jamais demander un départ déjà passé au moment où la requête part."""
    maintenant = datetime.now(FUSEAU)
    if date:
        h, m = (heure or f"{maintenant.hour:02d}:{maintenant.minute:02d}").split(":")
        dt_local = datetime.strptime(date, "%Y-%m-%d").replace(
            hour=int(h), minute=int(m), tzinfo=FUSEAU
        )
    elif heure:
        h, m = heure.split(":")
        dt_local = maintenant.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
    else:
        dt_local = maintenant + timedelta(seconds=30)
    return dt_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _etapes_depuis_reponse(route):
    etapes = []
    for leg in route.get("legs", []):
        for step in leg.get("steps", []):
            if step.get("travelMode") != "TRANSIT":
                etapes.append({"type": "marche"})
                continue
            details = step.get("transitDetails", {})
            ligne = details.get("transitLine", {})
            arrets = details.get("stopDetails", {})
            heures = details.get("localizedValues", {})
            etapes.append({
                "type": "transport",
                "ligne": ligne.get("nameShort") or ligne.get("name"),
                "mode": (ligne.get("vehicle") or {}).get("type"),
                "destination": details.get("headsign"),
                "arret_depart": (arrets.get("departureStop") or {}).get("name"),
                "arret_arrivee": (arrets.get("arrivalStop") or {}).get("name"),
                "depart": ((heures.get("departureTime") or {}).get("time") or {}).get("text"),
                "arrivee": ((heures.get("arrivalTime") or {}).get("time") or {}).get("text"),
            })
    return etapes


def calculer_itineraire_complexe(arret_depart_id, arret_arrivee_id, date=None, heure=None, conn=None):
    cle = os.environ.get("GOOGLE_ROUTES_API_KEY")
    if not cle:
        return {"trouve": False, "erreur": "calculateur complexe non configuré (GOOGLE_ROUTES_API_KEY absente)"}

    fermer = conn is None
    conn = conn or connexion_gtfs()
    index_arrets = {
        stop_id: arret
        for arret in charger_arrets_logiques(conn)
        for stop_id in arret["membres"]
    }
    if fermer:
        conn.close()

    arret_depart = index_arrets.get(arret_depart_id)
    arret_arrivee = index_arrets.get(arret_arrivee_id)
    if arret_depart is None or arret_arrivee is None:
        return {"trouve": False, "erreur": "arret_depart_id ou arret_arrivee_id inconnu"}

    corps = {
        "origin": {"location": {"latLng": {
            "latitude": arret_depart["lat"], "longitude": arret_depart["lon"],
        }}},
        "destination": {"location": {"latLng": {
            "latitude": arret_arrivee["lat"], "longitude": arret_arrivee["lon"],
        }}},
        "travelMode": "TRANSIT",
        "departureTime": _departure_time_rfc3339(date, heure),
    }

    try:
        reponse = httpx.post(BASE_URL, json=corps, headers=_en_tete(cle), timeout=TIMEOUT_SECONDES)
        reponse.raise_for_status()
    except httpx.HTTPError:
        return {"trouve": False, "erreur": "calculateur complexe indisponible (erreur réseau ou API Google)"}

    donnees = reponse.json()
    routes = donnees.get("routes") or []
    if not routes:
        return {"trouve": False, "erreur": "aucun trajet trouvé par le calculateur complexe"}

    etapes = _etapes_depuis_reponse(routes[0])
    if not etapes:
        return {"trouve": False, "erreur": "réponse du calculateur complexe vide ou inattendue"}

    duree_brute = routes[0].get("duration", "")
    duree_min = int(float(duree_brute.rstrip("s"))) // 60 if duree_brute else None

    return {"trouve": True, "etapes": etapes, "duree_totale_min": duree_min}
