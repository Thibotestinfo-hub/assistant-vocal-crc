"""
Point d'entrée pour le déploiement (Clever Cloud). Lit PORT depuis
l'environnement directement en Python, pour ne dépendre d'aucune
substitution de variable par un shell (CC_RUN_COMMAND exécute la
commande sans passer par un shell, donc "--port $PORT" ne fonctionne pas).

Lancement : python run.py
"""

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("assistant.api.main:app", host="0.0.0.0", port=port)
