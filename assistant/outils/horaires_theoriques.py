"""
Outil `horaires_theoriques` — renvoie les horaires prévus à un arrêt.
Contrat exact : docs/spec-assistant-vocal-v0-revisee.md, §4.

La brique neuve par rapport à l'Étape 2 : résoudre quel `service_id`
circule pour une DATE donnée (jour de la semaine + exceptions
calendar_dates), plutôt que de regarder tous les horaires toutes dates
confondues.
"""

import unicodedata
from datetime import date as Date
from datetime import datetime, timedelta

from assistant.outils.arrets import trouver_par_stop_id
from assistant.outils.db import connexion_gtfs

JOURS_SEMAINE = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _normaliser(texte):
    forme = unicodedata.normalize("NFD", texte or "")
    return "".join(c for c in forme if unicodedata.category(c) != "Mn").lower().strip()


def _formater_heure(secondes):
    h, reste = divmod(secondes, 3600)
    m = reste // 60
    return f"{h % 24:02d}:{m:02d}"


def _services_actifs(conn, date):
    """service_id actifs ce jour-là : règle hebdomadaire de calendar.txt,
    corrigée par les exceptions de calendar_dates.txt."""
    jour_colonne = JOURS_SEMAINE[date.weekday()]
    date_str = date.strftime("%Y%m%d")

    actifs = {
        row["service_id"]
        for row in conn.execute(
            f"SELECT service_id FROM calendar "
            f"WHERE start_date <= ? AND end_date >= ? AND {jour_colonne} = 1",
            (date_str, date_str),
        )
    }
    for row in conn.execute(
        "SELECT service_id, exception_type FROM calendar_dates WHERE date = ?",
        (date_str,),
    ):
        if row["exception_type"] == 1:
            actifs.add(row["service_id"])
        elif row["exception_type"] == 2:
            actifs.discard(row["service_id"])
    return actifs


def _type_service(date):
    """Étiquette indicative. Ce jeu GTFS est purement estival : la
    distinction "vacances_scolaires" n'est pas représentée dedans, donc
    cette étiquette ne peut pas encore la détecter (voir docs/fiche-gtfs.md)."""
    if date.weekday() == 6:
        return "dimanche_ferie"
    if date.weekday() == 5:
        return "samedi"
    return "semaine"


def _direction_correspond(direction_demandee, trip_row, route_row):
    if not direction_demandee:
        return True
    d = _normaliser(direction_demandee)
    if d == str(trip_row["direction_id"]):
        return True
    nom_direction = route_row["direction0_name"] if trip_row["direction_id"] == 0 else route_row["direction1_name"]
    return d in _normaliser(nom_direction or "")


def _departs_du_jour(conn, membres, date, ligne=None, direction=None):
    services = _services_actifs(conn, date)
    if not services:
        return []

    placeholders_membres = ",".join("?" * len(membres))
    placeholders_services = ",".join("?" * len(services))
    lignes = conn.execute(
        f"""
        SELECT st.departure_secondes, r.route_short_name, t.trip_headsign,
               t.direction_id, r.direction0_name, r.direction1_name
        FROM stop_times st
        JOIN trips t ON t.trip_id = st.trip_id
        JOIN routes r ON r.route_id = t.route_id
        WHERE st.stop_id IN ({placeholders_membres})
          AND t.service_id IN ({placeholders_services})
        """,
        (*membres, *services),
    ).fetchall()

    departs = []
    for row in lignes:
        if ligne and row["route_short_name"] != ligne:
            continue
        if direction and not _direction_correspond(direction, row, row):
            continue
        departs.append({
            "ligne": row["route_short_name"],
            "destination": row["trip_headsign"],
            "_secondes": row["departure_secondes"],
        })
    departs.sort(key=lambda d: d["_secondes"])
    return departs


def horaires_theoriques(arret_id, ligne=None, direction=None, type="prochains",
                         date=None, nb=3, conn=None):
    fermer = conn is None
    conn = conn or connexion_gtfs()

    arret = trouver_par_stop_id(arret_id, conn)
    if arret is None:
        if fermer:
            conn.close()
        return {"erreur": f"arret_id {arret_id!r} inconnu"}

    date_cible = datetime.strptime(date, "%Y-%m-%d").date() if date else Date.today()
    maintenant_secondes = None
    if type == "prochains" and (date is None or date_cible == Date.today()):
        maintenant = datetime.now()
        maintenant_secondes = maintenant.hour * 3600 + maintenant.minute * 60 + maintenant.second

    type_service = _type_service(date_cible)

    departs_jour = _departs_du_jour(conn, arret["membres"], date_cible, ligne, direction)
    # "circule aujourd'hui" doit porter sur CET arrêt (et cette ligne si précisée),
    # pas sur le réseau entier : un autre service peut très bien tourner ce
    # jour-là sans que la ligne demandée y soit.
    circule_aujourdhui = len(departs_jour) > 0

    premier = _formater_heure(departs_jour[0]["_secondes"]) if departs_jour else None
    dernier = _formater_heure(departs_jour[-1]["_secondes"]) if departs_jour else None

    departs_reponse = []
    if type == "prochains":
        source = departs_jour
        base_secondes = maintenant_secondes
        jours_decales = 0
        if maintenant_secondes is not None:
            source = [d for d in departs_jour if d["_secondes"] >= maintenant_secondes]
            # Plus aucun départ aujourd'hui : premier départ du lendemain (règle de la spec).
            if not source:
                lendemain = date_cible + timedelta(days=1)
                source = _departs_du_jour(conn, arret["membres"], lendemain, ligne, direction)
                jours_decales = 1
        for d in source[:nb]:
            secondes_absolues = d["_secondes"] + jours_decales * 86400
            dans_minutes = None
            if base_secondes is not None:
                dans_minutes = (secondes_absolues - base_secondes) // 60
            departs_reponse.append({
                "ligne": d["ligne"],
                "destination": d["destination"],
                "heure": _formater_heure(d["_secondes"]),
                "dans_minutes": dans_minutes,
            })

    if fermer:
        conn.close()

    return {
        "type_service": type_service,
        "circule_aujourdhui": circule_aujourdhui,
        "departs": departs_reponse,
        "premier": premier,
        "dernier": dernier,
    }
