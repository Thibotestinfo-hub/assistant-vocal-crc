"""
Dossier RGPD — droits des personnes (docs/audit-dsi.md, partie 6.6) :
recherche de tout ce qui est lié à un appelant, pour répondre à une
demande d'accès ou d'effacement.

Recherche par téléphone, jamais par nom : c'est le seul identifiant
présent dans les quatre tables qui peuvent porter une donnée
personnelle (appels, objets_perdus, demandes_rappel, sms_envoyes) —
"appels" n'a pas de colonne nom fiable, seulement le texte libre du
transcript (voir docs/prochaines-etapes.md, 28/10/2026).
"""

import csv
import io
import json

from assistant.outils.db import connexion_app, normaliser_telephone


def _resume_appel(donnees_brutes):
    """Titre court pour afficher un appel dans la liste, à partir du
    résumé déjà calculé par ElevenLabs (analysis.call_summary_title) —
    jamais recalculé ou deviné ici."""
    if not donnees_brutes or donnees_brutes == "{}":
        return "Transcript déjà supprimé (purge à 90 jours, partie 6.4 de l'audit)"
    try:
        charge = json.loads(donnees_brutes)
    except json.JSONDecodeError:
        return "Résumé indisponible"
    donnees = charge.get("data", charge) if isinstance(charge, dict) else {}
    analyse = donnees.get("analysis") or {}
    return analyse.get("call_summary_title") or "Appel (pas de résumé disponible)"


def _transcript_lisible(donnees_brutes):
    """Transcription complète en texte lisible (un tour par ligne),
    pour l'export RGPD — jamais le JSON brut tel quel."""
    if not donnees_brutes or donnees_brutes == "{}":
        return "(transcript déjà supprimé — purge à 90 jours)"
    try:
        charge = json.loads(donnees_brutes)
    except json.JSONDecodeError:
        return "(transcript illisible)"
    donnees = charge.get("data", charge) if isinstance(charge, dict) else {}
    lignes = [
        f"{tour.get('role', '?')} : {tour['message']}"
        for tour in (donnees.get("transcript") or [])
        if tour.get("message")
    ]
    return "\n".join(lignes) if lignes else "(aucun message dans le transcript)"


def rechercher_dossier(telephone):
    """Tout ce qui est lié à ce numéro, toutes tables confondues, trié
    par date décroissante. None si le numéro saisi n'est pas un numéro
    français valide (erreur de saisie de l'agent à corriger, pas une
    recherche vide)."""
    telephone = normaliser_telephone(telephone)
    if not telephone:
        return None

    conn = connexion_app()
    elements = []

    for l in conn.execute(
        "SELECT id, cree_le, donnees_brutes FROM appels WHERE telephone = ?", (telephone,)
    ):
        elements.append({
            "cle": f"appels:{l['id']}", "type": "Appel", "date": l["cree_le"],
            "resume": _resume_appel(l["donnees_brutes"]), "opt_in_marketing": None,
        })

    for l in conn.execute(
        "SELECT id, cree_le, nature, description, opt_in_marketing FROM objets_perdus "
        "WHERE telephone = ?", (telephone,)
    ):
        elements.append({
            "cle": f"objets_perdus:{l['id']}", "type": "Objet perdu", "date": l["cree_le"],
            "resume": f"{l['nature']} — {l['description']}",
            "opt_in_marketing": bool(l["opt_in_marketing"]),
        })

    for l in conn.execute(
        "SELECT id, cree_le, motif, resume, opt_in_marketing FROM demandes_rappel "
        "WHERE telephone = ?", (telephone,)
    ):
        elements.append({
            "cle": f"demandes_rappel:{l['id']}", "type": "Demande de rappel", "date": l["cree_le"],
            "resume": f"{l['motif']} — {l['resume']}",
            "opt_in_marketing": bool(l["opt_in_marketing"]),
        })

    for l in conn.execute(
        "SELECT id, cree_le, succes FROM sms_envoyes WHERE telephone = ?", (telephone,)
    ):
        elements.append({
            "cle": f"sms_envoyes:{l['id']}", "type": "SMS envoyé", "date": l["cree_le"],
            "resume": "Envoyé" if l["succes"] else "Échec d'envoi", "opt_in_marketing": None,
        })

    conn.close()
    elements.sort(key=lambda e: e["date"] or "", reverse=True)
    return {"telephone": telephone, "elements": elements}


def _detail_objet_perdu(l):
    return (
        f"Nature : {l['nature']}\nDescription : {l['description']}\n"
        f"Ligne : {l['ligne'] or '—'}  Sens : {l['sens'] or '—'}\n"
        f"Perdu le {l['date_perte']} ({l['creneau_horaire']}) à {l['lieu']}\n"
        f"Déclarant : {l['nom']}  Email : {l['email'] or '—'}\n"
        f"Consentement marketing : {'oui' if l['opt_in_marketing'] else 'non'}"
    )


def _detail_demande_rappel(l):
    return (
        f"Motif : {l['motif']}\nRésumé : {l['resume']}\n"
        f"Nom : {l['nom'] or '—'}  Email : {l['email'] or '—'}\n"
        f"Consentement marketing : {'oui' if l['opt_in_marketing'] else 'non'}"
    )


def _detail_sms(l):
    statut = "envoyé" if l["succes"] else f"échec — {l['erreur'] or 'cause inconnue'}"
    return f"Destinataire : {l['nom'] or '—'}\nStatut : {statut}\nTexte :\n{l['texte'] or '(non conservé)'}"


# table -> (colonnes à lire, libellé affiché, formateur de contenu)
_TABLES_DETAIL = {
    "appels": (
        "id, cree_le, conversation_id, telephone, donnees_brutes", "Appel",
        lambda l: _transcript_lisible(l["donnees_brutes"]),
    ),
    "objets_perdus": ("*", "Objet perdu", _detail_objet_perdu),
    "demandes_rappel": ("*", "Demande de rappel", _detail_demande_rappel),
    "sms_envoyes": ("*", "SMS envoyé", _detail_sms),
}


def obtenir_details(cles):
    """Détail complet de chaque élément coché (cle = 'table:id'), pour
    l'export CSV et la version imprimable — ignore une clé malformée ou
    inconnue plutôt que de faire échouer tout l'export pour une case
    cochée invalide."""
    conn = connexion_app()
    details = []
    for cle in cles:
        table, _, id_brut = cle.partition(":")
        if table not in _TABLES_DETAIL or not id_brut.isdigit():
            continue
        colonnes, libelle, formater = _TABLES_DETAIL[table]
        l = conn.execute(f"SELECT {colonnes} FROM {table} WHERE id = ?", (int(id_brut),)).fetchone()
        if not l:
            continue
        details.append({
            "type": libelle, "id": l["id"], "date": l["cree_le"],
            "telephone": l["telephone"] if "telephone" in l.keys() else None,
            "conversation_id": l["conversation_id"] if "conversation_id" in l.keys() else None,
            "contenu": formater(l),
        })
    conn.close()
    details.sort(key=lambda d: d["date"] or "", reverse=True)
    return details


def supprimer_elements(cles):
    """Droit à l'effacement sur les éléments cochés (cle = 'table:id').

    objets_perdus/demandes_rappel/sms_envoyes : la ligne entière est
    supprimée — c'est la donnée personnelle elle-même, même principe
    que supprimer_objet_perdu() dans exports.py.

    appels : jamais supprimée. La ligne est anonymisée exactement comme
    purger_transcripts_expires() (donnees_brutes et telephone vidés) —
    les colonnes de traçabilité (durée, coût, tokens...) n'ont rien de
    personnel et doivent survivre indéfiniment (CLAUDE.md : "non
    reconstituable après coup"). Supprimer la ligne perdrait ces
    métriques pour de bon, pas seulement la donnée personnelle visée.

    Renvoie le nombre d'éléments traités."""
    conn = connexion_app()
    n = 0
    for cle in cles:
        table, _, id_brut = cle.partition(":")
        if table not in _TABLES_DETAIL or not id_brut.isdigit():
            continue
        id_ = int(id_brut)
        if table == "appels":
            conn.execute("UPDATE appels SET donnees_brutes = '{}', telephone = NULL WHERE id = ?", (id_,))
        else:
            conn.execute(f"DELETE FROM {table} WHERE id = ?", (id_,))
        n += 1
    conn.commit()
    conn.close()
    return n


def exporter_details_csv(details):
    tampon = io.StringIO()
    ecrivain = csv.writer(tampon, delimiter=";")
    ecrivain.writerow(["type", "id", "date", "telephone", "conversation_id", "contenu"])
    for d in details:
        ecrivain.writerow([
            d["type"], d["id"], d["date"], d["telephone"] or "", d["conversation_id"] or "", d["contenu"],
        ])
    # BOM UTF-8 : même raison que assistant/backoffice/exports.py (Excel).
    return "﻿" + tampon.getvalue()
