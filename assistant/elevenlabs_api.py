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


def _agent_id():
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    return config["elevenlabs_agent_id"]


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


if __name__ == "__main__":
    print("Voix du compte :")
    for nom, voice_id in lister_voix():
        print(f"  {nom} -> {voice_id}")
    print()
    print("Voix actuelle de l'agent :", voix_actuelle())
