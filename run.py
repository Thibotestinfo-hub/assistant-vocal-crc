"""
Point d'entrée pour le déploiement (Clever Cloud). Lit PORT depuis
l'environnement directement en Python, pour ne dépendre d'aucune
substitution de variable par un shell (CC_RUN_COMMAND exécute la
commande sans passer par un shell, donc "--port $PORT" ne fonctionne pas).

Sur Clever Cloud, la variable PORT n'est pas fournie pour ce type
d'application : leur Nginx interne écoute sur 8080 en façade et
redirige vers le port 9000 ("Nginx will listen on port 8080, forward
to port 9000", vu dans les logs de déploiement) — c'est donc 9000 qu'il
faut utiliser par défaut, pas 8080 (qui entre en collision avec Nginx
lui-même).

Lancement : python run.py
"""

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9000))
    print(f"Démarrage sur le port {port}")
    uvicorn.run("assistant.api.main:app", host="0.0.0.0", port=port)
