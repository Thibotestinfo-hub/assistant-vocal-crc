"""
Point d'entrée pour le déploiement (Clever Cloud). Écoute en dur sur le
port 9000 : leur Nginx interne écoute sur 8080 en façade et redirige
vers le port 9000 ("Nginx will listen on port 8080, forward to port
9000", vu dans les logs de déploiement). La variable d'environnement
PORT, elle, vaut 8080 sur cette plateforme — la suivre entre directement
en collision avec Nginx ("address already in use"), donc on l'ignore
volontairement ici.

Lancement : python run.py
"""

import uvicorn

PORT = 9000

if __name__ == "__main__":
    print(f"Démarrage sur le port {PORT}", flush=True)
    uvicorn.run("assistant.api.main:app", host="0.0.0.0", port=PORT)
