"""
Point d'entrée pour le déploiement (Clever Cloud). Écoute en dur sur le
port 9000 : leur Nginx interne écoute sur 8080 en façade et redirige
vers le port 9000 ("Nginx will listen on port 8080, forward to port
9000", vu dans les logs de déploiement). La variable d'environnement
PORT, elle, vaut 8080 sur cette plateforme — la suivre entre directement
en collision avec Nginx ("address already in use"), donc on l'ignore
volontairement ici.

Avant de démarrer : si la base GTFS n'existe pas encore (c'est le cas au
tout premier démarrage sur un serveur neuf, data/gtfs.db n'étant jamais
commité), on la construit — téléchargement + chargement + enrichissement.

Lancement : python run.py
"""

from pathlib import Path

import uvicorn

from assistant.outils.db import DB_GTFS_PATH
from assistant.ingestion.provisionner import provisionner

PORT = 9000

if __name__ == "__main__":
    if not Path(DB_GTFS_PATH).exists():
        print("Base GTFS absente : construction au démarrage...", flush=True)
        provisionner()
    print(f"Démarrage sur le port {PORT}", flush=True)
    uvicorn.run("assistant.api.main:app", host="0.0.0.0", port=PORT)
