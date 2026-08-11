"""
Script de vérification : pour une liste de lignes données, affiche le
terminus et le premier/dernier départ de chaque direction, calculés à
partir de la base SQLite chargée par assistant.ingestion.charger_gtfs.

À comparer à la main avec les fiches horaires officielles du site du
réseau (https://www.salonetangcotebleue.fr/fr/horaires-de-ligne-en-pdf/96).

Usage : python3 tests/verifier_horaires.py 1 10 14
        (sans argument, vérifie 1, 10 et 14 par défaut)
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "gtfs.db"

LIGNES_PAR_DEFAUT = ["1", "10", "14"]


def formater_heure(secondes):
    h, reste = divmod(secondes, 3600)
    m = reste // 60
    if h >= 24:
        return f"{h - 24:02d}:{m:02d} (lendemain)"
    return f"{h:02d}:{m:02d}"


def verifier_ligne(conn, route_short_name):
    print(f"=== Ligne {route_short_name} ===")

    services = conn.execute(
        """
        SELECT DISTINCT c.service_id, c.service_name,
            c.monday, c.tuesday, c.wednesday, c.thursday, c.friday, c.saturday, c.sunday
        FROM trips t
        JOIN routes r ON t.route_id = r.route_id
        JOIN calendar c ON t.service_id = c.service_id
        WHERE r.route_short_name = ?
        """,
        (route_short_name,),
    ).fetchall()
    for s in services:
        jours = [j for j, actif in zip(
            ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"],
            [s["monday"], s["tuesday"], s["wednesday"], s["thursday"],
             s["friday"], s["saturday"], s["sunday"]]
        ) if actif]
        print(f"  Service {s['service_id']} ({s['service_name']}) : {', '.join(jours)}")

    for direction in (0, 1):
        origine = conn.execute(
            """
            SELECT s.stop_name, s.commune_gtfs
            FROM stop_times st
            JOIN trips t ON st.trip_id = t.trip_id
            JOIN routes r ON t.route_id = r.route_id
            JOIN stops s ON st.stop_id = s.stop_id
            WHERE r.route_short_name = ? AND t.direction_id = ?
              AND st.stop_sequence = (SELECT MIN(stop_sequence) FROM stop_times WHERE trip_id = t.trip_id)
            LIMIT 1
            """,
            (route_short_name, direction),
        ).fetchone()
        if origine is None:
            continue

        terminus = conn.execute(
            """
            SELECT s.stop_name, s.commune_gtfs
            FROM stop_times st
            JOIN trips t ON st.trip_id = t.trip_id
            JOIN routes r ON t.route_id = r.route_id
            JOIN stops s ON st.stop_id = s.stop_id
            WHERE r.route_short_name = ? AND t.direction_id = ?
              AND st.stop_sequence = (SELECT MAX(stop_sequence) FROM stop_times WHERE trip_id = t.trip_id)
            LIMIT 1
            """,
            (route_short_name, direction),
        ).fetchone()

        bornes = conn.execute(
            """
            SELECT MIN(st.departure_secondes) AS premier, MAX(st.departure_secondes) AS dernier
            FROM stop_times st
            JOIN trips t ON st.trip_id = t.trip_id
            JOIN routes r ON t.route_id = r.route_id
            WHERE r.route_short_name = ? AND t.direction_id = ?
              AND st.stop_sequence = (SELECT MIN(stop_sequence) FROM stop_times WHERE trip_id = t.trip_id)
            """,
            (route_short_name, direction),
        ).fetchone()

        print(f"  Direction {direction} : {origine['stop_name']} ({origine['commune_gtfs']}) "
              f"-> {terminus['stop_name']} ({terminus['commune_gtfs']})")
        print(f"    Premier départ : {formater_heure(bornes['premier'])}   "
              f"Dernier départ : {formater_heure(bornes['dernier'])}")
    print()


def main():
    lignes = sys.argv[1:] or LIGNES_PAR_DEFAUT
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    for ligne in lignes:
        verifier_ligne(conn, ligne)
    conn.close()


if __name__ == "__main__":
    main()
