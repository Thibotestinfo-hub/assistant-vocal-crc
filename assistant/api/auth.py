"""
Authentification par jeton bearer. Le jeton attendu vit dans .env
(jamais dans le dépôt) sous la clé API_TOKEN.

Chaque appel à l'API doit envoyer l'en-tête :
    Authorization: Bearer <API_TOKEN>
"""

import os

from dotenv import load_dotenv
from fastapi import Header, HTTPException

load_dotenv()

API_TOKEN = os.environ.get("API_TOKEN")

if not API_TOKEN:
    raise RuntimeError(
        "API_TOKEN absent de l'environnement. Vérifie que .env existe et "
        "contient API_TOKEN=... (voir .env, jamais commité)."
    )


def verifier_jeton(authorization: str = Header(default=None)):
    attendu = f"Bearer {API_TOKEN}"
    if authorization != attendu:
        raise HTTPException(status_code=401, detail="Jeton d'authentification invalide ou absent")
