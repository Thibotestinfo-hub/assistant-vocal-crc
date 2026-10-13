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
import unicodedata
from datetime import datetime

import httpx
import yaml
from pathlib import Path

from assistant.outils.db import connexion_app, horodatage, obtenir_parametre
from assistant.outils.horaires_theoriques import FUSEAU
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


def _sans_accents(texte):
    """Pour la version "texte" du SMS (garantie 100% GSM-7, voir
    docstring du module) : les noms d'arrêts et de communes réels
    contiennent des accents ("Plantée", "Émile Ripert"), contrairement
    aux textes qu'on écrit nous-mêmes dans ce fichier — il faut aussi
    les nettoyer, sinon un seul arrêt accentué suffit à faire basculer
    tout le SMS en UCS-2 malgré le format "texte" choisi."""
    if not texte:
        return texte
    forme = unicodedata.normalize("NFD", texte)
    return "".join(c for c in forme if unicodedata.category(c) != "Mn")


def _duree_libelle(minutes):
    """"1 h 09" au-delà d'une heure, "43 min" sinon — None si la durée
    totale n'est pas connue (jamais 0 par défaut)."""
    if minutes is None:
        return None
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes // 60} h {minutes % 60:02d}"


def _preparer_contexte_sms(etapes, duree_totale_min, destination):
    """Calcule, une seule fois, tout ce dont les deux formats de SMS ont
    besoin : temps d'attente avant chaque bus (déduit des horaires des
    étapes, jamais inventé — None si une donnée manque), heure réelle de
    départ à pied (si la première étape est une marche de durée connue)
    et heure d'arrivée finale réelle (horaire du dernier transport +
    marche finale si sa durée est connue). Une valeur manquante reste
    None et n'est simplement pas affichée par les formateurs (CLAUDE.md,
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

    heure_depart_reelle = None
    if etapes and etapes[0]["type"] == "marche" and etapes[0].get("duree_min") is not None and transports:
        premier_depart = _minutes(transports[0].get("depart"))
        if premier_depart is not None:
            heure_depart_reelle = _hhmm(premier_depart - etapes[0]["duree_min"])

    return {
        "etapes": etapes,
        "duree_totale_min": duree_totale_min,
        "duree_totale_libelle": _duree_libelle(duree_totale_min),
        "destination": destination,
        "nb_bus": nb_bus,
        "nb_changements": max(nb_bus - 1, 0),
        "heure_arrivee_finale": heure_arrivee_finale,
        "heure_depart_reelle": heure_depart_reelle,
        "heure_calcul": datetime.now(FUSEAU).strftime("%H:%M"),
    }


def _entete_resume(ctx, emoji):
    """En-tête commun aux deux formats : "Arrivée à X : HH:MM" puis
    "durée · N bus · N changements" — calqué sur la maquette fournie
    par l'utilisateur le 13/10/2026."""
    verbe = "Arrivée à" if emoji else "Arrivee a"
    separateur = " · " if emoji else " - "

    lignes = []
    dest = ctx["destination"].upper() if ctx["destination"] else None
    if dest and not emoji:
        dest = _sans_accents(dest)
    if dest and ctx["heure_arrivee_finale"]:
        lignes.append(f"{verbe} {dest} : {ctx['heure_arrivee_finale']}")
    elif dest:
        lignes.append(f"{verbe} {dest}")

    resume = []
    if ctx["duree_totale_libelle"]:
        resume.append(ctx["duree_totale_libelle"])
    if ctx["nb_bus"]:
        resume.append(f"{ctx['nb_bus']} bus")
        if ctx["nb_changements"]:
            mot = "changement" if ctx["nb_changements"] == 1 else "changements"
            resume.append(f"{ctx['nb_changements']} {mot}")
    if resume:
        lignes.append(separateur.join(resume))
    return lignes


def _formater_sms_emoji(ctx, nom):
    if nom:
        lignes = [f"Bonjour {nom}, voici votre itinéraire sur le réseau TABM", ""]
    else:
        lignes = ["Voici votre itinéraire sur le réseau TABM", ""]
    lignes += _entete_resume(ctx, emoji=True)
    lignes.append("")

    etapes = ctx["etapes"]
    transports = [e for e in etapes if e["type"] == "transport"]
    numero_transport = 0
    for i, etape in enumerate(etapes):
        if etape["type"] == "marche":
            duree, vers = etape.get("duree_min"), etape.get("vers")
            if i == 0:
                if ctx["heure_depart_reelle"] and duree and vers:
                    lignes.append(f"🚶 Départ {ctx['heure_depart_reelle']} · {duree} min à pied")
                    lignes.append(f"   vers {vers}")
                elif vers:
                    suffixe = f" (environ {duree} min)" if duree else ""
                    lignes.append(f"🚶 Marcher vers {vers}{suffixe}")
                lignes.append("")
            elif i == len(etapes) - 1:
                lignes.append(f"🚶 {duree} min à pied" if duree else "🚶 Marche à pied")
            else:
                lignes.append(f"🚶 {duree} min à pied" if duree else "🚶 Marche à pied")
                if vers:
                    lignes.append(f"   vers {vers}")
                lignes.append("")
        else:
            numero_transport += 1
            ligne, direction = etape.get("ligne") or "?", etape.get("destination") or "?"
            depart = etape.get("depart") or "?"
            lignes.append(f"{numero_transport}. 🚌 Ligne {ligne} · {depart}")
            lignes.append(f"Direction {direction}")
            arrivee = f", {etape['arrivee']}" if etape.get("arrivee") else ""
            lignes.append(f"🔻 Descendre {etape.get('arret_arrivee') or '?'}{arrivee}")
            prochain = transports[numero_transport] if numero_transport < len(transports) else None
            if prochain and prochain.get("attente_min") is not None:
                lignes.append(f"⏱ {prochain['attente_min']} min d'attente")
            lignes.append("")

    if ctx["heure_arrivee_finale"]:
        lignes.append(f"🏁 Arrivée {ctx['heure_arrivee_finale']}")
    lignes.append("")
    lignes.append(f"Horaires à jour à {ctx['heure_calcul']}")
    return "\n".join(lignes).strip("\n")


def _formater_sms_texte(ctx, nom):
    """Même contenu que la version emoji, sans aucun emoji ni caractère
    accentué (volontaire : garantit l'encodage GSM-7, 160 car./segment
    au lieu de 70 — voir docstring du module)."""
    if nom:
        lignes = [f"Bonjour {_sans_accents(nom)}, voici votre itineraire sur le reseau TABM", ""]
    else:
        lignes = ["Voici votre itineraire sur le reseau TABM", ""]
    lignes += _entete_resume(ctx, emoji=False)
    lignes.append("")

    etapes = ctx["etapes"]
    transports = [e for e in etapes if e["type"] == "transport"]
    numero_transport = 0
    for i, etape in enumerate(etapes):
        if etape["type"] == "marche":
            duree, vers = etape.get("duree_min"), _sans_accents(etape.get("vers"))
            if i == 0:
                if ctx["heure_depart_reelle"] and duree and vers:
                    lignes.append(f"Depart {ctx['heure_depart_reelle']} - {duree} min a pied")
                    lignes.append(f"   vers {vers}")
                elif vers:
                    suffixe = f" (environ {duree} min)" if duree else ""
                    lignes.append(f"Marcher vers {vers}{suffixe}")
                lignes.append("")
            elif i == len(etapes) - 1:
                lignes.append(f"{duree} min a pied" if duree else "Marche a pied")
            else:
                lignes.append(f"{duree} min a pied" if duree else "Marche a pied")
                if vers:
                    lignes.append(f"   vers {vers}")
                lignes.append("")
        else:
            numero_transport += 1
            ligne = _sans_accents(etape.get("ligne")) or "?"
            direction = _sans_accents(etape.get("destination")) or "?"
            depart = etape.get("depart") or "?"
            lignes.append(f"{numero_transport}. Bus ligne {ligne} - {depart}")
            lignes.append(f"Direction {direction}")
            arrivee = f", {etape['arrivee']}" if etape.get("arrivee") else ""
            lignes.append(f"Descendre a {_sans_accents(etape.get('arret_arrivee')) or '?'}{arrivee}")
            prochain = transports[numero_transport] if numero_transport < len(transports) else None
            if prochain and prochain.get("attente_min") is not None:
                lignes.append(f"Attente {prochain['attente_min']} min")
            lignes.append("")

    if ctx["heure_arrivee_finale"]:
        lignes.append(f"Arrivee {ctx['heure_arrivee_finale']}")
    lignes.append("")
    lignes.append(f"Horaires a jour a {ctx['heure_calcul']}")
    return "\n".join(lignes).strip("\n")


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


def envoyer_sms_itineraire(telephone, arret_depart_id, arret_arrivee_id, date=None, heure=None, nom=None, preference=None, conversation_id=None):
    """Fonction destinée à tourner en tâche de fond (voir route dans
    assistant/api/main.py) — ne lève jamais, consigne toujours un
    résultat dans sms_envoyes, même une erreur totalement imprévue
    (le try/except large est volontaire ici : une tâche de fond qui
    plante en silence, sans aucune trace, est pire qu'une ligne
    d'erreur — personne ne peut alors savoir qu'elle a échoué).

    preference : doit être la même valeur que celle passée à
    calculer_itineraire_complexe pendant l'appel, sinon le SMS
    recalculerait un trajet différent de celui annoncé à l'oral
    (CLAUDE.md, exactitude)."""
    try:
        resultat = calculer_itineraire_complexe(arret_depart_id, arret_arrivee_id, date, heure, preference)
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


def _compte_segments(texte):
    """Nombre de SMS effectivement facturés par Twilio pour un texte
    donné — calculé nous-mêmes à partir du texte réellement envoyé
    (déjà conservé dans sms_envoyes), plutôt que via un appel à l'API
    Twilio : aussi exact, sans dépendance réseau supplémentaire pour une
    simple page de suivi. Règle GSM-7 / UCS-2 (voir docstring du
    module) : un seul caractère hors GSM-7 (tout emoji, par exemple)
    force tout le message en UCS-2, qui tient 4x moins de caractères
    par segment. Nos deux formats ne mélangent jamais les deux dans un
    même SMS (le format texte est garanti 100% ASCII), donc "tout
    ASCII" suffit ici à distinguer les deux cas sans construire la
    table complète de l'alphabet GSM-7 étendu."""
    if not texte:
        return 0
    gsm7 = all(ord(c) < 128 for c in texte)
    taille_unique, taille_multi = (160, 153) if gsm7 else (70, 67)
    n = len(texte)
    return 1 if n <= taille_unique else -(-n // taille_multi)


def resumer_sms():
    """Agrège les SMS réellement envoyés (succès uniquement — un échec
    n'est jamais facturé) : nombre de SMS "logiques" et nombre réel de
    segments facturés par Twilio, pour l'indicateur back-office (voir
    assistant/backoffice/page.py, tuile qui a remplacé l'ancien
    "Horaire moyen des appels", devenu redondant avec l'histogramme
    horaire)."""
    conn = connexion_app()
    lignes = conn.execute("SELECT texte FROM sms_envoyes WHERE succes = 1").fetchall()
    conn.close()
    return {
        "nb_sms_envoyes": len(lignes),
        "nb_segments": sum(_compte_segments(l["texte"]) for l in lignes),
    }
