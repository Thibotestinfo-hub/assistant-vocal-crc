"""
Point d'entrée pour le déploiement (Clever Cloud). Écoute en dur sur le
port 9000 : leur Nginx interne écoute sur 8080 en façade et redirige
vers le port 9000 ("Nginx will listen on port 8080, forward to port
9000", vu dans les logs de déploiement). La variable d'environnement
PORT, elle, vaut 8080 sur cette plateforme — la suivre entre directement
en collision avec Nginx ("address already in use"), donc on l'ignore
volontairement ici.

Avant de démarrer, deux constructions si elles manquent (jamais
commitées, régénérées à chaque nouveau serveur) :
- data/gtfs.db : téléchargement + chargement + enrichissement du GTFS.
- data/corpus_index.json : extraction du site + découpage + vectorisation,
  pour rechercher_information. Plus long que le GTFS (télécharge un
  modèle d'environ 250-500 Mo la première fois).

Lancement : python run.py
"""

from pathlib import Path

import uvicorn

from assistant.ingestion.extraire_corpus import extraire_corpus
from assistant.ingestion.extraire_tarifs import ecrire_corpus, extraire_grille
from assistant.ingestion.indexer_corpus import INDEX_PATH, construire_index
from assistant.ingestion.provisionner import provisionner
from assistant.outils.db import DB_GTFS_PATH

PORT = 9000

if __name__ == "__main__":
    if not Path(DB_GTFS_PATH).exists():
        print("Base GTFS absente : construction au démarrage...", flush=True)
        provisionner()
    if not Path(INDEX_PATH).exists():
        print("Index documentaire absent : construction au démarrage...", flush=True)
        ecrire_corpus(extraire_grille())
        extraire_corpus()
        construire_index()
    print(f"Démarrage sur le port {PORT}", flush=True)
    uvicorn.run("assistant.api.main:app", host="0.0.0.0", port=PORT)
