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
    "routes.legs.steps.staticDuration,"
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


def _duree_min(duree_brute):
    """Convertit une durée Google au format '240s' en minutes entières,
    ou None si absente — jamais 0 par défaut (CLAUDE.md, exactitude :
    une durée inconnue ne doit jamais être confondue avec zéro minute)."""
    if not duree_brute:
        return None
    return int(float(duree_brute.rstrip("s"))) // 60


def _etapes_depuis_reponse(route, nom_arret_depart=None):
    # À plat : une étape de marche a besoin de connaître l'arrêt de
    # l'étape SUIVANTE pour dire "marcher vers..." (voir docs/
    # prochaines-etapes.md, 12/10/2026) — plus simple de travailler sur
    # une liste de steps indexable que sur l'imbrication legs/steps.
    steps = [s for leg in route.get("legs", []) for s in leg.get("steps", [])]
    etapes = []
    # Référence pour détecter une marche "vers" l'endroit où l'on est déjà
    # (artefact Google : changement de quai, ou léger écart entre nos
    # coordonnées moyennées du GTFS et le point qu'il choisit) — initialisée
    # avec l'arrêt de départ puisque la toute première marche, s'il y en a
    # une, part justement de là.
    dernier_arret = nom_arret_depart
    i = 0
    while i < len(steps):
        step = steps[i]
        if step.get("travelMode") != "TRANSIT":
            # Google découpe parfois une seule marche réelle en plusieurs
            # steps techniques (ex. traverser une rue) — on les fusionne
            # en une seule étape "marche", sinon le SMS/l'oral répète
            # "Marche" plusieurs fois pour un même trajet à pied (vu en
            # conditions réelles le 12/10/2026).
            duree_min = 0
            duree_connue = False
            j = i
            while j < len(steps) and steps[j].get("travelMode") != "TRANSIT":
                d = _duree_min(steps[j].get("staticDuration"))
                if d is not None:
                    duree_min += d
                    duree_connue = True
                j += 1
            vers = None
            if j < len(steps) and steps[j].get("travelMode") == "TRANSIT":
                arret_suivant = steps[j].get("transitDetails", {}).get("stopDetails", {})
                vers = (arret_suivant.get("departureStop") or {}).get("name")
            duree_finale = duree_min if duree_connue else None
            # Rien d'utile à annoncer si on "marche" vers l'endroit où l'on
            # est déjà, et que ce n'est pas une vraie marche (courte ou
            # durée inconnue) — sinon on garde l'info, une vraie
            # correspondance avec marche peut partager le même nom d'arrêt
            # tout en étant un vrai trajet à pied.
            if not (vers and vers == dernier_arret and (duree_finale is None or duree_finale <= 2)):
                etapes.append({"type": "marche", "duree_min": duree_finale, "vers": vers})
            i = j
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
        dernier_arret = etapes[-1]["arret_arrivee"]
        i += 1
    return etapes


def _lien_google_maps(arret_depart, arret_arrivee):
    """Lien universel Google Maps (web/iOS/Android), trajet pré-rempli en
    mode transport en commun — aucun appel API, aucun coût, juste les
    coordonnées qu'on a déjà résolues pour l'appel à Google Routes.
    Arrondi à 5 décimales (~1 m de précision, largement suffisant pour
    un arrêt de bus) : la précision brute de la moyenne GTFS fait un
    lien deux fois plus long pour rien, important dans un SMS compté en
    caractères (voir docs/prochaines-etapes.md, 12/10/2026)."""
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={arret_depart['lat']:.5f},{arret_depart['lon']:.5f}"
        f"&destination={arret_arrivee['lat']:.5f},{arret_arrivee['lon']:.5f}"
        "&travelmode=transit"
    )


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

    etapes = _etapes_depuis_reponse(routes[0], arret_depart.get("stop_name"))
    if not etapes:
        return {"trouve": False, "erreur": "réponse du calculateur complexe vide ou inattendue"}

    return {
        "trouve": True,
        "etapes": etapes,
        "duree_totale_min": _duree_min(routes[0].get("duration")),
        "lien_google_maps": _lien_google_maps(arret_depart, arret_arrivee),
    }
