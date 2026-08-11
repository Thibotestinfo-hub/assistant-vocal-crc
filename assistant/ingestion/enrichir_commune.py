"""
Déduit la commune de chaque arrêt à partir de ses coordonnées GPS, en
testant dans quel contour communal (polygone) chaque arrêt tombe.

Le GTFS ne fournit pas la commune nativement (le champ `city_name` vu
dans ce jeu est une extension propriétaire Mecatran, pas garantie sur un
autre réseau) : cette déduction géographique est la méthode portable.

Source des contours : "france-geojson" (open data, licence ouverte),
un fichier par département. Le périmètre du réseau tient entièrement
dans le département 13 (Bouches-du-Rhône) d'après les codes INSEE
observés dans data/gtfs/stops.txt.

Usage : python3 -m assistant.ingestion.enrichir_commune
(à lancer après assistant.ingestion.charger_gtfs)
"""

import json
import sqlite3
import urllib.request
from pathlib import Path

from shapely.geometry import Point, shape

RACINE = Path(__file__).resolve().parent.parent.parent
DB_PATH = RACINE / "data" / "gtfs.db"
CONTOURS_PATH = RACINE / "data" / "communes-13.geojson"
CONTOURS_URL = (
    "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/"
    "departements/13-bouches-du-rhone/communes-13-bouches-du-rhone.geojson"
)


def telecharger_contours():
    if not CONTOURS_PATH.exists():
        print(f"Téléchargement des contours communaux depuis {CONTOURS_URL}")
        urllib.request.urlretrieve(CONTOURS_URL, CONTOURS_PATH)
    with open(CONTOURS_PATH, encoding="utf-8") as f:
        return json.load(f)


def enrichir():
    geojson = telecharger_contours()
    # Pour chaque commune : (nom, code_insee, polygone shapely)
    communes = [
        (
            feature["properties"]["nom"],
            feature["properties"]["code"],
            shape(feature["geometry"]),
        )
        for feature in geojson["features"]
    ]

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    stops = conn.execute("SELECT stop_id, stop_lat, stop_lon FROM stops").fetchall()

    non_trouves = []
    for stop in stops:
        point = Point(stop["stop_lon"], stop["stop_lat"])
        commune_trouvee = None
        for nom, code_insee, polygone in communes:
            if polygone.contains(point):
                commune_trouvee = nom
                break
        if commune_trouvee is None:
            non_trouves.append(stop["stop_id"])
        conn.execute(
            "UPDATE stops SET commune = ? WHERE stop_id = ?",
            (commune_trouvee, stop["stop_id"]),
        )
    conn.commit()

    print(f"{len(stops)} arrêts traités, {len(non_trouves)} sans commune trouvée.")
    if non_trouves:
        print("  Arrêts non résolus (hors des polygones du département 13) :",
              non_trouves[:10])

    # --- Vérification croisée avec commune_gtfs, notre seule référence connue ---
    # france-geojson stocke les noms de commune SANS article ("Pennes-Mirabeau"),
    # alors que commune_gtfs les a AVEC ("Les Pennes-Mirabeau") : on l'ignore
    # pour isoler les vrais désaccords des différences purement cosmétiques.
    def sans_article(nom):
        for article in ("Les ", "Le ", "La ", "L'"):
            if nom.startswith(article):
                return nom[len(article):]
        return nom

    desaccords = conn.execute(
        "SELECT stop_id, stop_name, commune, commune_gtfs FROM stops "
        "WHERE commune_gtfs IS NOT NULL AND commune_gtfs != '' AND commune != commune_gtfs"
    ).fetchall()
    n_avec_reference = conn.execute(
        "SELECT COUNT(*) FROM stops WHERE commune_gtfs IS NOT NULL AND commune_gtfs != ''"
    ).fetchone()[0]

    vrais_desaccords = [d for d in desaccords if sans_article(d["commune_gtfs"]) != d["commune"]]
    n_cosmetiques = len(desaccords) - len(vrais_desaccords)

    print(f"\nComparaison avec commune_gtfs (référence fournie par le réseau) : "
          f"{n_avec_reference - len(desaccords)}/{n_avec_reference} identiques, "
          f"{n_cosmetiques} différences d'article seulement (« Les Pennes-Mirabeau » "
          f"vs « Pennes-Mirabeau »), {len(vrais_desaccords)} vrais désaccords.")
    if vrais_desaccords:
        print("Vrais désaccords (commune différente, pas juste l'article) :")
        for d in vrais_desaccords:
            print(f"  {d['stop_id']} ({d['stop_name']}) : "
                  f"calculé={d['commune']!r} vs déclaré={d['commune_gtfs']!r}")

    conn.close()


if __name__ == "__main__":
    enrichir()
