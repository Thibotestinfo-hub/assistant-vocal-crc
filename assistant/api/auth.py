"""
Authentification par jeton bearer. Le jeton attendu vit dans .env
(jamais dans le dépôt) sous la clé API_TOKEN.

Chaque appel à l'API doit envoyer l'en-tête :
    Authorization: Bearer <API_TOKEN>

Le back-office utilise un mot de passe séparé (BACKOFFICE_MOT_DE_PASSE),
volontairement distinct d'API_TOKEN depuis le 29/09/2026 (voir
docs/audit-dsi.md, partie 5.4) : API_TOKEN circule par nature dans des
endroits publics ou semi-publics (en-têtes d'outils ElevenLabs, URL de
webhook, captures d'écran de configuration) ; le compromettre ne doit
jamais donner accès aux journaux d'appels du back-office.
"""

import os
import secrets

from dotenv import load_dotenv
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

load_dotenv()

API_TOKEN = os.environ.get("API_TOKEN")
BACKOFFICE_MOT_DE_PASSE = os.environ.get("BACKOFFICE_MOT_DE_PASSE")

if not API_TOKEN:
    raise RuntimeError(
        "API_TOKEN absent de l'environnement. Vérifie que .env existe et "
        "contient API_TOKEN=... (voir .env, jamais commité)."
    )

if not BACKOFFICE_MOT_DE_PASSE:
    raise RuntimeError(
        "BACKOFFICE_MOT_DE_PASSE absent de l'environnement. Choisis un mot "
        "de passe indépendant d'API_TOKEN et ajoute-le à .env (jamais "
        "commité) et aux variables d'environnement Clever Cloud."
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
    """Protection de la page de back-office (identifiant/mot de passe
    classiques dans le navigateur), avec BACKOFFICE_MOT_DE_PASSE — jamais
    API_TOKEN, qui circule dans des endroits bien moins protégés (voir
    docstring du module)."""
    mot_de_passe_ok = secrets.compare_digest(identifiants.password, BACKOFFICE_MOT_DE_PASSE)
    utilisateur_ok = secrets.compare_digest(identifiants.username, "crc")
    if not (mot_de_passe_ok and utilisateur_ok):
        raise HTTPException(
            status_code=401, detail="Accès refusé",
            headers={"WWW-Authenticate": "Basic"},
        )
