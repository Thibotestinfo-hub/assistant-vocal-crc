"""
Appels à l'API ElevenLabs elle-même (pas les webhooks qu'elle nous
envoie) — pour l'instant, uniquement changer la voix de l'agent depuis
notre propre back-office, sans que l'équipe CRC ait besoin d'un compte
ElevenLabs pendant le POC (voir docs/prochaines-etapes.md).

Nécessite ELEVENLABS_API_KEY dans l'environnement (.env en local) :
une clé de compte ElevenLabs, différente de notre propre API_TOKEN.
Jamais commitée, jamais loggée.

Usage de vérification : python3 -m assistant.elevenlabs_api
"""

import os
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

load_dotenv()

RACINE = Path(__file__).resolve().parent.parent
CONFIG_PATH = RACINE / "data" / "config.yaml"
BASE_URL = "https://api.elevenlabs.io/v1"


def _config():
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def _agent_id():
    return _config()["elevenlabs_agent_id"]


def voix_disponibles():
    """Les 2-3 voix proposées à l'équipe CRC (data/config.yaml), pas
    toutes les voix du compte — voir la note dans config.yaml sur
    pourquoi cette liste est statique plutôt qu'interrogée en direct."""
    return _config().get("voix_disponibles", [])


def nom_voix(voice_id):
    """Nom lisible d'une voix connue, ou l'identifiant technique tel
    quel si elle ne fait pas partie de voix_disponibles (ex. une voix
    testée manuellement puis retirée de la config)."""
    for voix in voix_disponibles():
        if voix["id"] == voice_id:
            return voix["nom"]
    return voice_id


def _en_tete():
    cle = os.environ.get("ELEVENLABS_API_KEY")
    if not cle:
        raise RuntimeError("ELEVENLABS_API_KEY absente de l'environnement (.env)")
    return {"xi-api-key": cle}


def lister_voix():
    """Renvoie [(nom, voice_id), ...] pour toutes les voix du compte."""
    reponse = httpx.get(f"{BASE_URL}/voices", headers=_en_tete(), timeout=15)
    reponse.raise_for_status()
    return [(v["name"], v["voice_id"]) for v in reponse.json()["voices"]]


def obtenir_agent():
    """Config complète de l'agent telle que renvoyée par ElevenLabs —
    utile pour vérifier avant/après un changement."""
    reponse = httpx.get(f"{BASE_URL}/convai/agents/{_agent_id()}", headers=_en_tete(), timeout=15)
    reponse.raise_for_status()
    return reponse.json()


def voix_actuelle():
    return obtenir_agent()["conversation_config"]["tts"]["voice_id"]


def changer_voix_agent(voice_id):
    """Change la voix de l'agent. Renvoie la voix effectivement en
    place juste après (nouvelle requête GET, pas la réponse du PATCH) :
    c'est ce qui nous dira si le changement est immédiat ou s'il faut
    un geste de publication en plus, question ouverte à ce stade."""
    corps = {"conversation_config": {"tts": {"voice_id": voice_id}}}
    reponse = httpx.patch(
        f"{BASE_URL}/convai/agents/{_agent_id()}", headers=_en_tete(), json=corps, timeout=15,
    )
    reponse.raise_for_status()
    return voix_actuelle()


def changer_reglages_voix(voice_id=None, stability=None, style=None):
    """Change la voix et/ou les réglages de ton (stability) et de style
    de l'agent, en un seul appel. Champs non fournis (None) : pas
    envoyés à ElevenLabs, donc pas modifiés — comportement PATCH partiel
    déjà vérifié pour voice_id seul (25/08/2026), supposé identique ici
    tant qu'on n'a pas revérifié spécifiquement pour stability/style.

    stability et style : documentés par ElevenLabs sur
    conversation_config.tts, 0.0 à 1.0. Renvoie la config tts effective
    juste après (nouvelle requête GET), même logique de vérification
    que changer_voix_agent."""
    tts = {}
    if voice_id:
        tts["voice_id"] = voice_id
    if stability is not None:
        tts["stability"] = stability
    if style is not None:
        tts["style"] = style
    if not tts:
        return obtenir_agent()["conversation_config"]["tts"]

    corps = {"conversation_config": {"tts": tts}}
    reponse = httpx.patch(
        f"{BASE_URL}/convai/agents/{_agent_id()}", headers=_en_tete(), json=corps, timeout=15,
    )
    reponse.raise_for_status()
    return obtenir_agent()["conversation_config"]["tts"]


def lister_conversations(exclude_statuses=None):
    """Conversations de l'agent telles que renvoyées par ElevenLabs.
    D'après leur documentation, chaque conversation porte un statut
    (initiated / in-progress / processing / done / failed) — de quoi
    construire un panneau "appels en cours" sans attendre le webhook de
    fin d'appel, qui lui n'arrive qu'à la toute fin.

    Jamais appelée depuis le back-office pour l'instant : la vraie forme
    de la réponse n'a pas encore été vérifiée sur un appel réel (réseau
    ElevenLabs bloqué depuis l'environnement où cette fonction a été
    écrite — voir python3 -m assistant.elevenlabs_api, à exécuter
    depuis un environnement qui a accès à internet, ex. Codespaces).
    Ne pas construire d'écran dessus avant d'avoir vérifié cette forme
    pour de vrai (CLAUDE.md, Vérifiabilité)."""
    params = {"agent_id": _agent_id()}
    if exclude_statuses:
        params["exclude_statuses"] = exclude_statuses
    reponse = httpx.get(f"{BASE_URL}/convai/conversations", headers=_en_tete(), params=params, timeout=15)
    reponse.raise_for_status()
    return reponse.json()


if __name__ == "__main__":
    import json as _json

    print("Voix du compte :")
    for nom, voice_id in lister_voix():
        print(f"  {nom} -> {voice_id}")
    print()
    print("Voix actuelle de l'agent :", voix_actuelle())
    print()
    print("Conversations (à vérifier avant de construire 'appels en cours') :")
    print(_json.dumps(lister_conversations(), ensure_ascii=False, indent=2))
