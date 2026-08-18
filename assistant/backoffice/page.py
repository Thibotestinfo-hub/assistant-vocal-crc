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


def page_detail_appel(appel):
    donnees_brutes = json.dumps(json.loads(appel["donnees_brutes"]), ensure_ascii=False, indent=2)
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Appel {html.escape(str(appel['id']))} — Assistant Étang</title>
<style>
  body {{ font-family: sans-serif; margin: 2rem; }}
  pre {{ background: #f5f5f5; padding: 1rem; overflow-x: auto; white-space: pre-wrap; }}
</style>
</head>
<body>
<p><a href="/backoffice/appels">&larr; retour à la liste</a></p>
<h1>Appel {html.escape(str(appel['id']))}</h1>
<p>Reçu le {html.escape(appel['cree_le'])} — conversation {html.escape(appel['conversation_id'] or '—')} — statut {html.escape(appel['statut'] or '—')}</p>
<h2>Charge brute reçue du webhook</h2>
<pre>{html.escape(donnees_brutes)}</pre>
</body>
</html>"""
