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

Deux formats de SMS (voir docs/prochaines-etapes.md, 13/10/2026),
choisis depuis le back-office (table "parametres", clé "format_sms") :
- "emoji" (par défaut) : plus lisible, pour les démos — mais tout
  emoji force tout le SMS en encodage UCS-2 (70 car./segment au lieu de
  160), donc 2 à 3x plus cher à l'usage.
- "texte" : aucun emoji, aucun caractère accentué (volontairement, pour
  rester en encodage GSM-7 à 160 car./segment) — même contenu, format
  pensé pour un déploiement à grande échelle plutôt que pour l'effet
  démo.
Les deux s'appuient sur le même calcul (_preparer_contexte_sms), pour
ne jamais faire dire des choses différentes aux deux formats.

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

from assistant.outils.db import connexion_app, horodatage, obtenir_parametre
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


# --- calculs partagés par les deux formats (jamais de texte en dur, tout
# vient des étapes structurées renvoyées par calculer_itineraire_complexe) ---

def _minutes(hhmm):
    """'HH:MM' -> minutes depuis minuit, ou None si absent/invalide."""
    if not hhmm:
        return None
    try:
        h, m = hhmm.split(":")
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return None


def _hhmm(total_minutes):
    total_minutes %= 24 * 60
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def _preparer_contexte_sms(etapes, duree_totale_min, destination):
    """Calcule, une seule fois, tout ce dont les deux formats de SMS ont
    besoin : temps d'attente avant chaque bus (déduit des horaires des
    étapes, jamais inventé — None si une donnée manque) et heure
    d'arrivée finale réelle (horaire du dernier transport + marche
    finale si sa durée est connue). Une valeur manquante reste None et
    n'est simplement pas affichée par les formateurs (CLAUDE.md,
    exactitude : on ne remplace jamais une donnée absente par une
    approximation)."""
    etapes = [dict(e) for e in etapes]  # copie : on ajoute attente_min sans modifier l'original

    heure_dispo = None  # minute à laquelle on est libre de repartir, ou None si la chaîne est rompue
    for etape in etapes:
        if etape["type"] == "marche":
            duree = etape.get("duree_min")
            heure_dispo = heure_dispo + duree if (heure_dispo is not None and duree is not None) else None
        else:
            depart = _minutes(etape.get("depart"))
            attente = (depart - heure_dispo) if (heure_dispo is not None and depart is not None) else None
            etape["attente_min"] = attente if (attente is not None and attente >= 0) else None
            heure_dispo = _minutes(etape.get("arrivee"))

    transports = [e for e in etapes if e["type"] == "transport"]
    nb_bus = len(transports)

    heure_arrivee_finale = None
    if transports:
        idx_dernier_transport = etapes.index(transports[-1])
        base = _minutes(transports[-1].get("arrivee"))
        marche_finale = 0
        for etape in etapes[idx_dernier_transport + 1:]:
            if etape.get("duree_min") is None:
                marche_finale = None
                break
            marche_finale += etape["duree_min"]
        if base is not None and marche_finale is not None:
            heure_arrivee_finale = _hhmm(base + marche_finale)

    return {
        "etapes": etapes,
        "duree_totale_min": duree_totale_min,
        "destination": destination,
        "nb_bus": nb_bus,
        "nb_correspondances": max(nb_bus - 1, 0),
        "heure_arrivee_finale": heure_arrivee_finale,
    }


def _formater_sms_emoji(ctx, nom):
    titre = f"📋 Bonjour {nom}, itinéraire TABM" if nom else "📋 Récap itinéraire TABM"
    lignes = [titre]

    resume = []
    if ctx["duree_totale_min"] is not None:
        resume.append(f"⏱ {ctx['duree_totale_min']} min")
    if ctx["nb_bus"]:
        resume.append(f"{ctx['nb_bus']} bus")
        if ctx["nb_correspondances"]:
            mot = "correspondance" if ctx["nb_correspondances"] == 1 else "correspondances"
            resume.append(f"{ctx['nb_correspondances']} {mot}")
    if resume:
        lignes.append(" • ".join(resume))
    lignes.append("")

    numero = 1
    for etape in ctx["etapes"]:
        if etape["type"] == "marche":
            duree, vers = etape.get("duree_min"), etape.get("vers")
            if vers and duree:
                lignes.append(f"{numero}. 🚶 Marcher vers {vers} (environ {duree} min)")
            elif vers:
                lignes.append(f"{numero}. 🚶 Marcher vers {vers}")
            else:
                lignes.append(f"{numero}. 🚶 Marche" + (f" (environ {duree} min)" if duree else ""))
        else:
            ligne, direction = etape.get("ligne") or "?", etape.get("destination") or "?"
            lignes.append(f"{numero}. 🚌 Ligne {ligne} - direction {direction}")
            if etape.get("attente_min") is not None:
                lignes.append(f"   🔁 Attente environ {etape['attente_min']} min, départ {etape.get('depart') or '?'}")
            elif etape.get("depart"):
                lignes.append(f"   Départ {etape['depart']}")
            arrivee = f", arrivée {etape['arrivee']}" if etape.get("arrivee") else ""
            lignes.append(f"   Descendre à {etape.get('arret_arrivee') or '?'}{arrivee}")
        numero += 1

    lignes.append("")
    arrivee_ligne = f"🏁 Arrivée à {ctx['destination']}" if ctx["destination"] else "🏁 Arrivée à destination"
    if ctx["heure_arrivee_finale"]:
        arrivee_ligne += f" vers {ctx['heure_arrivee_finale']}"
    lignes.append(arrivee_ligne)
    return "\n".join(lignes)


def _formater_sms_texte(ctx, nom):
    """Même contenu que la version emoji, sans aucun emoji ni caractère
    accentué (volontaire : garantit l'encodage GSM-7, 160 car./segment
    au lieu de 70 — voir docstring du module)."""
    titre = f"Bonjour {nom}, itineraire TABM" if nom else "Recap itineraire TABM"
    lignes = [titre]

    resume = []
    if ctx["duree_totale_min"] is not None:
        resume.append(f"{ctx['duree_totale_min']} min")
    if ctx["nb_bus"]:
        resume.append(f"{ctx['nb_bus']} bus")
        if ctx["nb_correspondances"]:
            mot = "correspondance" if ctx["nb_correspondances"] == 1 else "correspondances"
            resume.append(f"{ctx['nb_correspondances']} {mot}")
    if resume:
        lignes.append(" - ".join(resume))
    lignes.append("")

    numero = 1
    for etape in ctx["etapes"]:
        if etape["type"] == "marche":
            duree, vers = etape.get("duree_min"), etape.get("vers")
            if vers and duree:
                lignes.append(f"{numero}. Marcher vers {vers} (environ {duree} min)")
            elif vers:
                lignes.append(f"{numero}. Marcher vers {vers}")
            else:
                lignes.append(f"{numero}. Marche" + (f" (environ {duree} min)" if duree else ""))
        else:
            ligne, direction = etape.get("ligne") or "?", etape.get("destination") or "?"
            lignes.append(f"{numero}. Bus ligne {ligne}, direction {direction}")
            if etape.get("attente_min") is not None:
                lignes.append(f"   Attente environ {etape['attente_min']} min, depart {etape.get('depart') or '?'}")
            elif etape.get("depart"):
                lignes.append(f"   Depart {etape['depart']}")
            arrivee = f", arrivee {etape['arrivee']}" if etape.get("arrivee") else ""
            lignes.append(f"   Descendre a {etape.get('arret_arrivee') or '?'}{arrivee}")
        numero += 1

    lignes.append("")
    arrivee_ligne = f"Arrivee a {ctx['destination']}" if ctx["destination"] else "Arrivee a destination"
    if ctx["heure_arrivee_finale"]:
        arrivee_ligne += f" vers {ctx['heure_arrivee_finale']}"
    lignes.append(arrivee_ligne)
    return "\n".join(lignes)


def formater_sms_itineraire(etapes, duree_totale_min, nom=None, lien_google_maps=None, destination=None):
    """Construit le texte du SMS à partir des étapes structurées
    renvoyées par calculer_itineraire_complexe — jamais de texte libre
    en entrée (voir docstring du module). Le format (emoji ou texte) est
    choisi depuis le back-office, "emoji" par défaut si jamais réglé."""
    ctx = _preparer_contexte_sms(etapes, duree_totale_min, destination)
    format_choisi = obtenir_parametre("format_sms", "emoji")
    texte = _formater_sms_texte(ctx, nom) if format_choisi == "texte" else _formater_sms_emoji(ctx, nom)
    if lien_google_maps:
        prefixe = "Lien : " if format_choisi == "texte" else "📍 Voir sur Google Maps : "
        texte += "\n\n" + prefixe + lien_google_maps
    return texte


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
            resultat["etapes"], resultat.get("duree_totale_min"), nom,
            resultat.get("lien_google_maps"), resultat.get("destination"),
        )
        succes, erreur = _envoyer_requete_twilio(telephone, texte)
        _consigner(telephone, nom, texte, succes, erreur, conversation_id)
    except Exception as exc:
        _consigner(telephone, nom, None, False, f"erreur imprévue : {exc!r}", conversation_id)
