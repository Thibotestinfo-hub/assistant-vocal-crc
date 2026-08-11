"""
Charge le GTFS "Les bus de l'étang" (mamp-bde) depuis data/gtfs/ dans une
base SQLite (data/gtfs.db).

Recrée la base à chaque exécution (elle est entièrement dérivée des
fichiers GTFS, rien ne s'y ajoute à la main).

Usage : python3 -m assistant.ingestion.charger_gtfs
"""

import csv
import sqlite3
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent.parent
GTFS_DIR = RACINE / "data" / "gtfs"
DB_PATH = RACINE / "data" / "gtfs.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

# Le chargeur alerte si le GTFS expire dans moins de ce nombre de jours.
SEUIL_ALERTE_EXPIRATION_JOURS = 30


def lire_csv(nom):
    with open(GTFS_DIR / nom, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def heure_en_secondes(t):
    """'24:30:00' -> 88200. Fonctionne tel quel pour les heures >= 24h :
    c'est justement le but, pas de cas particulier à gérer."""
    h, m, s = (int(x) for x in t.split(":"))
    return h * 3600 + m * 60 + s


def charger():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    agency = lire_csv("agency.txt")
    conn.executemany(
        "INSERT INTO agency (agency_id, agency_name, agency_url, agency_phone) "
        "VALUES (:agency_id, :agency_name, :agency_url, :agency_phone)",
        agency,
    )

    stops = lire_csv("stops.txt")
    conn.executemany(
        "INSERT INTO stops (stop_id, stop_code, stop_name, stop_lat, stop_lon, "
        "location_type, parent_station, wheelchair_boarding, commune_gtfs) "
        "VALUES (:stop_id, :stop_code, :stop_name, :stop_lat, :stop_lon, "
        ":location_type, :parent_station, :wheelchair_boarding, :city_name)",
        stops,
    )

    routes = lire_csv("routes.txt")
    conn.executemany(
        "INSERT INTO routes (route_id, agency_id, route_short_name, route_long_name, "
        "route_type, direction0_name, direction1_name) "
        "VALUES (:route_id, :agency_id, :route_short_name, :route_long_name, "
        ":route_type, :direction0_name, :direction1_name)",
        routes,
    )

    trips = lire_csv("trips.txt")
    conn.executemany(
        "INSERT INTO trips (trip_id, route_id, service_id, trip_headsign, direction_id) "
        "VALUES (:trip_id, :route_id, :service_id, :trip_headsign, :direction_id)",
        trips,
    )

    stop_times = lire_csv("stop_times.txt")
    lignes_stop_times = [
        {
            "trip_id": st["trip_id"],
            "stop_id": st["stop_id"],
            "stop_sequence": int(st["stop_sequence"]),
            "arrival_secondes": heure_en_secondes(st["arrival_time"]),
            "departure_secondes": heure_en_secondes(st["departure_time"]),
            "pickup_type": int(st["pickup_type"] or 0),
            "drop_off_type": int(st["drop_off_type"] or 0),
        }
        for st in stop_times
    ]
    conn.executemany(
        "INSERT INTO stop_times (trip_id, stop_id, stop_sequence, arrival_secondes, "
        "departure_secondes, pickup_type, drop_off_type) "
        "VALUES (:trip_id, :stop_id, :stop_sequence, :arrival_secondes, "
        ":departure_secondes, :pickup_type, :drop_off_type)",
        lignes_stop_times,
    )

    calendar = lire_csv("calendar.txt")
    conn.executemany(
        "INSERT INTO calendar (service_id, monday, tuesday, wednesday, thursday, "
        "friday, saturday, sunday, start_date, end_date, service_name) "
        "VALUES (:service_id, :monday, :tuesday, :wednesday, :thursday, :friday, "
        ":saturday, :sunday, :start_date, :end_date, :service_name)",
        calendar,
    )

    calendar_dates = lire_csv("calendar_dates.txt")
    conn.executemany(
        "INSERT INTO calendar_dates (service_id, date, exception_type) "
        "VALUES (:service_id, :date, :exception_type)",
        calendar_dates,
    )

    conn.commit()

    # --- Résumé et alerte de validité ---
    feed_info = lire_csv("feed_info.txt")[0]
    fin_validite = date(
        int(feed_info["feed_end_date"][:4]),
        int(feed_info["feed_end_date"][4:6]),
        int(feed_info["feed_end_date"][6:8]),
    )
    jours_restants = (fin_validite - date.today()).days

    print(f"Base chargée : {DB_PATH}")
    print(f"  {len(stops)} arrêts, {len(routes)} lignes, {len(trips)} courses, "
          f"{len(stop_times)} dessertes")

    if jours_restants <= SEUIL_ALERTE_EXPIRATION_JOURS:
        print(f"⚠️  ALERTE : ce GTFS expire dans {jours_restants} jours "
              f"(le {fin_validite.isoformat()}). Il faut en télécharger un "
              f"nouveau bientôt.")
    else:
        print(f"Validité : encore {jours_restants} jours (jusqu'au {fin_validite.isoformat()}).")

    conn.close()


if __name__ == "__main__":
    charger()
