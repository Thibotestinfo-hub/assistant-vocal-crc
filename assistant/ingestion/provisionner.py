"""
Construit la base GTFS à partir de rien : télécharge le GTFS, le
décompresse, charge la base, enrichit les communes. C'est ce que le
serveur exécute tout seul à froid (data/gtfs.db n'est jamais commité,
voir .gitignore) — utile aussi bien en local qu'en production.

Usage : python3 -m assistant.ingestion.provisionner
"""

import zipfile
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

import yaml

from assistant.ingestion import charger_gtfs, enrichir_commune

RACINE = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = RACINE / "data" / "config.yaml"
GTFS_DIR = RACINE / "data" / "gtfs"


def telecharger_et_decompresser_gtfs():
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    print(f"Téléchargement du GTFS depuis {config['gtfs_url']}", flush=True)
    with urlopen(config["gtfs_url"], timeout=60) as reponse:
        contenu = reponse.read()

    GTFS_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(BytesIO(contenu)) as archive:
        archive.extractall(GTFS_DIR)
    print(f"GTFS décompressé dans {GTFS_DIR}", flush=True)


def provisionner():
    if not (GTFS_DIR / "stops.txt").exists():
        telecharger_et_decompresser_gtfs()
    else:
        print("GTFS déjà présent, pas de nouveau téléchargement.", flush=True)

    charger_gtfs.charger()
    enrichir_commune.enrichir()


if __name__ == "__main__":
    provisionner()
