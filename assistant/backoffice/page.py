"""Rendu HTML minimal de la liste des appels. Volontairement simple
(pas de framework front) : à améliorer visuellement une fois le fond
en place, voir docs/methode-developpement.md, Étape 6."""

import html
import json


def page_liste_appels(appels):
    lignes_html = "\n".join(
        f"<tr>"
        f"<td>{html.escape(a['cree_le'])}</td>"
        f"<td>{html.escape(a['conversation_id'] or '—')}</td>"
        f"<td>{html.escape(a['statut'] or '—')}</td>"
        f"<td><a href='/backoffice/appels/{a['id']}'>détail</a></td>"
        f"</tr>"
        for a in appels
    )
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Historique des appels — Assistant Étang</title>
<style>
  body {{ font-family: sans-serif; margin: 2rem; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ccc; padding: 0.5rem; text-align: left; }}
  th {{ background: #f0f0f0; }}
</style>
</head>
<body>
<h1>Historique des appels</h1>
<p>
  <a href="/backoffice/activation">Activation des outils</a> ·
  Exports :
  <a href="/backoffice/exports/objets_perdus.csv">objets perdus (CSV)</a> ·
  <a href="/backoffice/exports/demandes_rappel.csv">demandes de rappel (CSV)</a>
</p>
<p>{len(appels)} appel(s) — les {len(appels)} plus récents.</p>
<table>
<tr><th>Date</th><th>Conversation</th><th>Statut</th><th></th></tr>
{lignes_html}
</table>
</body>
</html>"""


def page_detail_appel(appel, evaluations=()):
    donnees_brutes = json.dumps(json.loads(appel["donnees_brutes"]), ensure_ascii=False, indent=2)

    if evaluations:
        lignes_eval = "\n".join(
            f"<li><strong>{'👍 bonne' if e['qualite'] == 'bonne' else '👎 mauvaise'}</strong> "
            f"— {html.escape(e['cree_le'])}"
            + (f" — {html.escape(e['note'])}" if e["note"] else "")
            + "</li>"
            for e in evaluations
        )
        bloc_evaluations = f"<ul>{lignes_eval}</ul>"
    else:
        bloc_evaluations = "<p>Aucune évaluation pour l'instant.</p>"

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Appel {html.escape(str(appel['id']))} — Assistant Étang</title>
<style>
  body {{ font-family: sans-serif; margin: 2rem; }}
  pre {{ background: #f5f5f5; padding: 1rem; overflow-x: auto; white-space: pre-wrap; }}
  textarea {{ width: 100%; max-width: 40rem; height: 4rem; font-family: inherit; }}
  .boutons button {{ padding: 0.5rem 1rem; margin-right: 0.5rem; cursor: pointer; }}
</style>
</head>
<body>
<p><a href="/backoffice/appels">&larr; retour à la liste</a></p>
<h1>Appel {html.escape(str(appel['id']))}</h1>
<p>Reçu le {html.escape(appel['cree_le'])} — conversation {html.escape(appel['conversation_id'] or '—')} — statut {html.escape(appel['statut'] or '—')}</p>

<h2>Évaluer cet appel</h2>
<form method="post" action="/backoffice/appels/{appel['id']}/evaluer">
  <textarea name="note" placeholder="Note libre, optionnelle : ce qui n'allait pas, la question posée, la réponse attendue..."></textarea>
  <div class="boutons">
    <button type="submit" name="qualite" value="bonne">👍 Bonne réponse</button>
    <button type="submit" name="qualite" value="mauvaise">👎 Mauvaise réponse</button>
  </div>
</form>

<h2>Évaluations précédentes</h2>
{bloc_evaluations}

<h2>Charge brute reçue du webhook</h2>
<pre>{html.escape(donnees_brutes)}</pre>
</body>
</html>"""


_NOMS_LISIBLES = {
    "rechercher_arret": "Identifier un arrêt",
    "horaires_theoriques": "Horaires théoriques",
    "rechercher_information": "Questions tarifs / pratique (FAQ)",
    "enregistrer_objet_perdu": "Déclarer un objet perdu",
    "demander_rappel": "Demander à être rappelé",
    "transferer_agent": "Transfert vers un conseiller",
}


def page_activations(activations):
    tous_actif = activations["tous"]

    def _ligne(cle, libelle):
        actif = activations["outils"][cle] if cle != "tous" else tous_actif
        etat = "activé" if actif else "désactivé"
        classe = "on" if actif else "off"
        bouton = "Désactiver" if actif else "Activer"
        return f"""<tr class="{classe}">
<td>{html.escape(libelle)}</td>
<td>{etat}</td>
<td>
  <form method="post" action="/backoffice/activation/{cle}/basculer" style="display:inline">
    <button type="submit">{bouton}</button>
  </form>
</td>
</tr>"""

    lignes_outils = "\n".join(
        _ligne(cle, libelle) for cle, libelle in _NOMS_LISIBLES.items()
    )

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Activation des outils — Assistant Étang</title>
<style>
  body {{ font-family: sans-serif; margin: 2rem; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
  th, td {{ border: 1px solid #ccc; padding: 0.6rem; text-align: left; }}
  th {{ background: #f0f0f0; }}
  tr.on td:nth-child(2) {{ color: #1a7f1a; font-weight: bold; }}
  tr.off td:nth-child(2) {{ color: #b00; font-weight: bold; }}
  .general {{ background: {"#eaffea" if tous_actif else "#ffecec"}; padding: 1rem; border-radius: 6px; }}
  button {{ padding: 0.4rem 0.9rem; cursor: pointer; }}
</style>
</head>
<body>
<p><a href="/backoffice/appels">&larr; historique des appels</a></p>
<h1>Activation des outils</h1>

<div class="general">
  <strong>Interrupteur général : {"activé" if tous_actif else "désactivé"}</strong><br>
  Coupe tout d'un coup, quel que soit le réglage de chaque outil ci-dessous.
  <form method="post" action="/backoffice/activation/tous/basculer">
    <button type="submit">{"Désactiver l'assistant" if tous_actif else "Activer l'assistant"}</button>
  </form>
</div>

<table>
<tr><th>Cas d'usage</th><th>État</th><th></th></tr>
{lignes_outils}
</table>

<p>Un outil désactivé ne casse pas l'appel : l'agent le traite comme une information indisponible et propose un transfert, exactement comme en cas de panne technique.</p>
</body>
</html>"""
