"""
Authentification par jeton bearer. Le jeton attendu vit dans .env
(jamais dans le dépôt) sous la clé API_TOKEN.

Chaque appel à l'API doit envoyer l'en-tête :
    Authorization: Bearer <API_TOKEN>
"""

import os
import secrets

from dotenv import load_dotenv
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

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


def verifier_jeton_requete(jeton: str = None):
    """Même vérification, mais via un paramètre d'URL (?jeton=...) plutôt
    qu'un en-tête : pour le webhook ElevenLabs, dont la configuration ne
    permet pas forcément d'ajouter un en-tête personnalisé, contrairement
    aux outils qu'on déclare nous-mêmes."""
    if not jeton or not secrets.compare_digest(jeton, API_TOKEN):
        raise HTTPException(status_code=401, detail="Jeton d'authentification invalide ou absent")


_basic = HTTPBasic()


def verifier_acces_backoffice(identifiants: HTTPBasicCredentials = Depends(_basic)):
    """Protection minimale de la page de back-office (identifiant/mot de
    passe classiques dans le navigateur) : le mot de passe est le même
    jeton que le reste de l'API. À revoir avant tout accès par de vraies
    données de voyageurs (voir CLAUDE.md, Étape 7)."""
    jeton_ok = secrets.compare_digest(identifiants.password, API_TOKEN)
    utilisateur_ok = secrets.compare_digest(identifiants.username, "crc")
    if not (jeton_ok and utilisateur_ok):
        raise HTTPException(
            status_code=401, detail="Accès refusé",
            headers={"WWW-Authenticate": "Basic"},
        )
