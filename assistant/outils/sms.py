"""
Outil `envoyer_sms_itineraire` — expérimental, désactivé par défaut.
Contrat : docs/spec-assistant-vocal-v0-revisee.md, §4.

Envoie par SMS (Twilio) le détail d'un itinéraire calculé par
`calculer_itineraire_complexe` (assistant/outils/itineraire_google.py).
Décision de conception (voir docs/prochaines-etapes.md, 12/10/2026) :

- Le texte du SMS n'est JAMAIS composé par le LLM. Cet outil recalcule
  l'itinéraire lui-même à partir des mêmes paramètres, et construit le
  texte depuis ce résultat structuré — jamais depuis ce que l'agent
  pourrait reformuler ou déformer (CLAUDE.md, exactitude).
- L'envoi réel (recalcul + appel Twilio) se fait en tâche de fond,
  après que la route ait répondu : on ne veut pas ajouter la latence
  d'un deuxième appel Google (déjà 400-600 ms mesurés, voir
  itineraire_google.py) ni celle de Twilio par-dessus, au milieu d'un
  tour de parole en direct.

Nécessite TWILIO_ACCOUNT_SID et TWILIO_AUTH_TOKEN dans l'environnement.
Absents, l'envoi échoue proprement (consigné dans sms_envoyes), jamais
d'exception qui remonterait jusqu'à la conversation — cette tâche
tourne de toute façon après coup, l'appelant ne peut plus être informé
d'un échec par la voix à ce stade.
"""

import os

import httpx
import yaml
from pathlib import Path

from assistant.outils.db import connexion_app, horodatage
from assistant.outils.itineraire_google import calculer_itineraire_complexe

RACINE = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = RACINE / "data" / "config.yaml"

TWILIO_URL_MODELE = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


def _config():
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def _numero_envoi():
    return _config()["twilio_numero_envoi"]


def _vers_e164(telephone):
    """Twilio attend un numéro au format international. Nos numéros sont
    validés en entrée (schemas.py, _valider_telephone) comme un format
    français à 10 chiffres commençant par 0 — jamais stockés normalisés
    (espaces possibles), donc toujours à nettoyer ici avant l'envoi."""
    nettoye = telephone.replace(" ", "").replace(".", "").replace("-", "")
    return "+33" + nettoye[1:]


def _ligne_marche(etape):
    duree = etape.get("duree_min")
    vers = etape.get("vers")
    if vers and duree:
        return f"🚶 Marcher vers {vers} (environ {duree} min)"
    if vers:
        return f"🚶 Marcher vers {vers}"
    if duree:
        return f"🚶 Marche, environ {duree} min"
    return "🚶 Marche"


def formater_sms_itineraire(etapes, duree_totale_min, nom=None, lien_google_maps=None):
    """Construit le texte du SMS à partir des étapes structurées
    renvoyées par calculer_itineraire_complexe — jamais de texte libre
    en entrée (voir docstring du module). Format pensé pour se
    rapprocher de ce qu'on voit sur Google Maps : ligne, direction
    (panneau du bus) et arrêt de descente clairement séparés, pas
    fondus dans une seule flèche."""
    titre = f"📋 Bonjour {nom}, voici votre itinéraire TABM" if nom else "📋 Récap de votre itinéraire TABM"
    lignes = [titre, ""]
    premiere_transport = True
    for etape in etapes:
        if etape["type"] == "marche":
            lignes.append(_ligne_marche(etape))
        else:
            if not premiere_transport:
                lignes.append("🔄 Correspondance")
            premiere_transport = False
            ligne = etape.get("ligne") or "?"
            direction = etape.get("destination") or "?"
            arret_arrivee = etape.get("arret_arrivee") or "?"
            lignes.append(f"🚌 Ligne {ligne} - direction {direction}")
            lignes.append(f"   Descendre à {arret_arrivee}")
            if etape.get("depart"):
                lignes.append(f"   Départ {etape['depart']}")
    lignes.append("")
    if duree_totale_min is not None:
        lignes.append(f"⏱ Durée totale : {duree_totale_min} min")
    if lien_google_maps:
        lignes.append("")
        lignes.append(f"📍 Voir sur Google Maps : {lien_google_maps}")
    return "\n".join(lignes)


def _envoyer_requete_twilio(telephone, texte):
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    jeton = os.environ.get("TWILIO_AUTH_TOKEN")
    if not sid or not jeton:
        return False, "Twilio non configuré (TWILIO_ACCOUNT_SID ou TWILIO_AUTH_TOKEN absent)"

    try:
        reponse = httpx.post(
            TWILIO_URL_MODELE.format(sid=sid),
            auth=(sid, jeton),
            data={"To": _vers_e164(telephone), "From": _numero_envoi(), "Body": texte},
            timeout=10.0,
        )
        reponse.raise_for_status()
    except httpx.HTTPError as exc:
        return False, f"échec de l'envoi Twilio : {exc}"
    return True, None


def _consigner(telephone, nom, texte, succes, erreur, conversation_id):
    conn = connexion_app()
    conn.execute(
        "INSERT INTO sms_envoyes (cree_le, telephone, nom, texte, succes, erreur, conversation_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (horodatage(), telephone, nom, texte, int(succes), erreur, conversation_id),
    )
    conn.commit()
    conn.close()


def envoyer_sms_itineraire(telephone, arret_depart_id, arret_arrivee_id, date=None, heure=None, nom=None, conversation_id=None):
    """Fonction destinée à tourner en tâche de fond (voir route dans
    assistant/api/main.py) — ne lève jamais, consigne toujours un
    résultat dans sms_envoyes, même une erreur totalement imprévue
    (le try/except large est volontaire ici : une tâche de fond qui
    plante en silence, sans aucune trace, est pire qu'une ligne
    d'erreur — personne ne peut alors savoir qu'elle a échoué)."""
    try:
        resultat = calculer_itineraire_complexe(arret_depart_id, arret_arrivee_id, date, heure)
        if not resultat.get("trouve"):
            _consigner(telephone, nom, None, False, resultat.get("erreur") or "itinéraire introuvable au moment de l'envoi", conversation_id)
            return

        texte = formater_sms_itineraire(
            resultat["etapes"], resultat.get("duree_totale_min"), nom, resultat.get("lien_google_maps"),
        )
        succes, erreur = _envoyer_requete_twilio(telephone, texte)
        _consigner(telephone, nom, texte, succes, erreur, conversation_id)
    except Exception as exc:
        _consigner(telephone, nom, None, False, f"erreur imprévue : {exc!r}", conversation_id)
