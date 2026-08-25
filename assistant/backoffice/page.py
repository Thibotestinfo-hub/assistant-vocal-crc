"""Rendu HTML du back-office — une seule page consolidée (historique des
appels, activation des outils, indicateurs, exports), sans framework
front : accordéon natif (<details>/<summary>) pour ouvrir un appel sans
recharger la page, formulaires HTML classiques pour les actions.

Palette de couleurs fournie par l'équipe CRC (Étape 6, retour visuel) :
bleu clair, sauge, rouge, rose — première mouture, à affiner ensemble."""

import html
import json

BLEU = "#A6D7E4"
SAUGE = "#C7DFD4"
ROUGE = "#FF6666"
ROSE = "#FFB6C8"

_NOMS_LISIBLES = {
    "rechercher_arret": "Identifier un arrêt",
    "horaires_theoriques": "Horaires théoriques",
    "rechercher_information": "Questions tarifs / pratique (FAQ)",
    "enregistrer_objet_perdu": "Déclarer un objet perdu",
    "demander_rappel": "Demander à être rappelé",
    "transferer_agent": "Transfert vers un conseiller",
}

_STYLE = f"""
:root {{
  --bleu: {BLEU};
  --sauge: {SAUGE};
  --rouge: {ROUGE};
  --rose: {ROSE};
  --texte: #22303c;
  --texte-doux: #6b7a86;
  --fond: #f7f9fa;
  --carte: #ffffff;
  --bordure: #e6ebee;
}}
* {{ box-sizing: border-box; }}
body {{
  font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background: var(--fond);
  color: var(--texte);
  margin: 0;
  padding: 0 0 4rem;
}}
a {{ color: #2b6a80; }}
header.entete {{
  background: var(--carte);
  border-bottom: 3px solid var(--bleu);
  padding: 1.4rem 2.5rem;
  display: flex;
  align-items: center;
  gap: 0.9rem;
}}
header.entete .logo {{
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 9px;
  background: linear-gradient(135deg, var(--bleu), var(--rose));
  flex-shrink: 0;
}}
header.entete h1 {{
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}}
header.entete .sous-titre {{
  color: var(--texte-doux);
  font-size: 0.85rem;
  margin-top: 0.15rem;
}}
main {{
  max-width: 68rem;
  margin: 0 auto;
  padding: 2rem 2.5rem;
}}
.grille-compteurs {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}}
.compteur {{
  background: var(--carte);
  border: 1px solid var(--bordure);
  border-top: 4px solid var(--accent, var(--bleu));
  border-radius: 10px;
  padding: 1.1rem 1.2rem;
}}
.compteur .valeur {{
  font-size: 1.7rem;
  font-weight: 700;
}}
.compteur .libelle {{
  color: var(--texte-doux);
  font-size: 0.8rem;
  margin-top: 0.2rem;
}}
.compteur.a-venir {{
  opacity: 0.55;
}}
.compteur.a-venir .valeur {{
  font-size: 1rem;
  font-weight: 500;
}}
.section {{
  background: var(--carte);
  border: 1px solid var(--bordure);
  border-radius: 10px;
  padding: 1.4rem 1.6rem;
  margin-bottom: 1.5rem;
}}
.section h2 {{
  font-size: 1rem;
  margin: 0 0 1rem;
}}
.bandeau-actions {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin-bottom: 1.5rem;
}}
.bouton, button {{
  font-family: inherit;
  font-size: 0.85rem;
  padding: 0.5rem 1rem;
  border-radius: 7px;
  border: 1px solid var(--bordure);
  background: var(--carte);
  color: var(--texte);
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
}}
.bouton:hover, button:hover {{ filter: brightness(0.96); }}
.bouton.accent {{ background: var(--bleu); border-color: var(--bleu); font-weight: 600; }}
.bandeau-actions button, .bandeau-actions .bouton {{ background: {BLEU}33; border-color: {BLEU}88; font-weight: 500; }}
button[name="qualite"][value="bonne"] {{ background: {SAUGE}77; border-color: {SAUGE}; }}
button[name="qualite"][value="mauvaise"] {{ background: {ROUGE}22; border-color: {ROUGE}77; }}
.interrupteur-general {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.9rem 1.1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  background: {SAUGE}55;
}}
.interrupteur-general.coupe {{ background: {ROUGE}22; }}
.interrupteur-general strong {{ font-size: 0.95rem; }}
.interrupteur-general button {{ background: var(--rouge); color: #fff; border-color: var(--rouge); font-weight: 600; }}
.interrupteur-general.coupe button {{ background: {SAUGE}; color: var(--texte); border-color: {SAUGE}; }}
.outils-grille {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
  gap: 0.6rem;
}}
.outil {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.6rem 0.9rem;
  border: 1px solid var(--bordure);
  border-radius: 8px;
  font-size: 0.85rem;
}}
.outil .pastille {{
  display: inline-block;
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  margin-right: 0.5rem;
}}
.outil.on {{ border-color: {SAUGE}; }}
.outil.on .pastille {{ background: #4a9d76; }}
.outil.off .pastille {{ background: var(--rouge); }}
.outil form {{ margin: 0; }}
.outil button {{ padding: 0.25rem 0.6rem; font-size: 0.75rem; }}
details.appel {{
  border: 1px solid var(--bordure);
  border-radius: 8px;
  margin-bottom: 0.6rem;
  overflow: hidden;
}}
details.appel summary {{
  list-style: none;
  cursor: pointer;
  padding: 0.8rem 1.1rem;
  display: flex;
  gap: 1rem;
  align-items: center;
  font-size: 0.85rem;
}}
details.appel summary::-webkit-details-marker {{ display: none; }}
details.appel summary .date {{ color: var(--texte-doux); min-width: 9rem; }}
details.appel summary .conv {{ font-family: monospace; color: var(--texte-doux); flex: 1; }}
details.appel[open] summary {{ border-bottom: 1px solid var(--bordure); }}
.corps-appel {{ padding: 1.1rem; }}
.corps-appel pre {{
  background: var(--fond);
  padding: 0.9rem;
  border-radius: 6px;
  overflow-x: auto;
  white-space: pre-wrap;
  font-size: 0.78rem;
  max-height: 20rem;
  overflow-y: auto;
}}
.corps-appel textarea {{
  width: 100%;
  max-width: 32rem;
  height: 3.2rem;
  font-family: inherit;
  border: 1px solid var(--bordure);
  border-radius: 6px;
  padding: 0.5rem;
}}
.evaluations-passees {{ font-size: 0.8rem; color: var(--texte-doux); margin: 0.6rem 0; }}
.badge-eval {{ padding: 0.1rem 0.5rem; border-radius: 5px; font-size: 0.75rem; }}
.badge-eval.bonne {{ background: {SAUGE}88; }}
.badge-eval.mauvaise {{ background: {ROUGE}33; }}
"""


def _details_ouvertes(id_cible):
    return "open" if id_cible else ""


def _bloc_appel(a):
    donnees_brutes = json.dumps(json.loads(a["donnees_brutes"]), ensure_ascii=False, indent=2)
    evaluations = a.get("evaluations", [])
    if evaluations:
        lignes_eval = "".join(
            f'<div><span class="badge-eval {"bonne" if e["qualite"] == "bonne" else "mauvaise"}">'
            f'{"👍 bonne" if e["qualite"] == "bonne" else "👎 mauvaise"}</span> '
            f'{html.escape(e["cree_le"])}'
            + (f' — {html.escape(e["note"])}' if e["note"] else "")
            + "</div>"
            for e in evaluations
        )
        bloc_evaluations = f'<div class="evaluations-passees">{lignes_eval}</div>'
    else:
        bloc_evaluations = '<p class="evaluations-passees">Aucune évaluation pour l\'instant.</p>'

    return f"""<details class="appel" id="appel-{a['id']}">
  <summary>
    <span class="date">{html.escape(a['cree_le'])}</span>
    <span class="conv">{html.escape(a['conversation_id'] or '—')}</span>
    <span>{html.escape(a['statut'] or '—')}</span>
  </summary>
  <div class="corps-appel">
    <h3 style="font-size:0.85rem;margin:0 0 0.5rem">Évaluer cet appel</h3>
    <form method="post" action="/backoffice/appels/{a['id']}/evaluer">
      <textarea name="note" placeholder="Note libre, optionnelle : ce qui n'allait pas, la question posée, la réponse attendue..."></textarea>
      <div style="margin-top:0.5rem">
        <button type="submit" name="qualite" value="bonne">👍 Bonne réponse</button>
        <button type="submit" name="qualite" value="mauvaise">👎 Mauvaise réponse</button>
      </div>
    </form>
    {bloc_evaluations}
    <h3 style="font-size:0.85rem;margin:1rem 0 0.5rem">Charge brute reçue du webhook</h3>
    <pre>{html.escape(donnees_brutes)}</pre>
  </div>
</details>"""


def _bloc_outils(activations):
    tous_actif = activations["tous"]

    def _ligne(cle, libelle):
        actif = activations["outils"][cle]
        classe = "on" if actif else "off"
        bouton = "Désactiver" if actif else "Activer"
        return f"""<div class="outil {classe}">
  <span><span class="pastille"></span>{html.escape(libelle)}</span>
  <form method="post" action="/backoffice/activation/{cle}/basculer">
    <button type="submit">{bouton}</button>
  </form>
</div>"""

    lignes_outils = "".join(_ligne(cle, libelle) for cle, libelle in _NOMS_LISIBLES.items())

    return f"""<div class="section">
  <h2>Expérimentation</h2>
  <div class="interrupteur-general {'coupe' if not tous_actif else ''}">
    <strong>{"🟢 Assistant en service" if tous_actif else "🔴 Assistant à l'arrêt"}</strong>
    <form method="post" action="/backoffice/activation/tous/basculer">
      <button type="submit">{"Tout arrêter" if tous_actif else "Tout relancer"}</button>
    </form>
  </div>
  <div class="outils-grille">
    {lignes_outils}
  </div>
</div>"""


def _formater_duree(secs):
    if secs is None:
        return "à venir"
    m, s = divmod(secs, 60)
    return f"{m} min {s:02d}" if m else f"{s} s"


def _formater_repartition(repartition):
    if not repartition:
        return "à venir", "Répartition par type de requête"
    total = sum(repartition.values())
    outil_principal, n = max(repartition.items(), key=lambda kv: kv[1])
    libelle_principal = _NOMS_LISIBLES.get(outil_principal, outil_principal)
    detail = ", ".join(
        f"{_NOMS_LISIBLES.get(o, o)} : {c}" for o, c in sorted(repartition.items(), key=lambda kv: -kv[1])
    )
    return f"{libelle_principal} ({n}/{total})", f"Type de requête le plus fréquent — {detail}"


def page_backoffice(appels, activations, nb_appels, satisfaction, tracabilite):
    bonnes, total_eval = satisfaction
    if total_eval:
        pct = f"{round(100 * bonnes / total_eval)}%"
        libelle_satisfaction = f"{bonnes}/{total_eval} évaluations"
    else:
        pct = "—"
        libelle_satisfaction = "aucune évaluation pour l'instant"

    duree_valeur = _formater_duree(tracabilite["duree_moyenne_secs"])
    horaire_valeur = tracabilite["horaire_moyen"] or "à venir"
    repartition_valeur, repartition_libelle = _formater_repartition(tracabilite["repartition_outils"])
    cout_valeur = f"{tracabilite['cout_total_usd']:.3f} $" if tracabilite["cout_total_usd"] is not None else "à venir"
    n_trace = tracabilite["nb_avec_tracabilite"]
    suffixe_trace = f" — sur {n_trace} appel{'s' if n_trace > 1 else ''}" if n_trace else ""

    blocs_appels = "\n".join(_bloc_appel(a) for a in appels) if appels else "<p>Aucun appel pour l'instant.</p>"

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Back-office — Assistant vocal CRC, zone Étang</title>
<style>{_STYLE}</style>
</head>
<body>
<header class="entete">
  <div class="logo"></div>
  <div>
    <h1>Assistant vocal CRC — zone Étang</h1>
    <div class="sous-titre">Suivi de l'expérimentation</div>
  </div>
</header>
<main>

  <div class="grille-compteurs">
    <div class="compteur" style="--accent:{BLEU}">
      <div class="valeur">{nb_appels}</div>
      <div class="libelle">Appels captés</div>
    </div>
    <div class="compteur" style="--accent:{ROSE}">
      <div class="valeur">{pct}</div>
      <div class="libelle">Satisfaction — {libelle_satisfaction}</div>
    </div>
    <div class="compteur{' a-venir' if tracabilite['duree_moyenne_secs'] is None else ''}" style="--accent:{SAUGE}">
      <div class="valeur">{duree_valeur}</div>
      <div class="libelle">Durée moyenne d'appel{suffixe_trace}</div>
    </div>
    <div class="compteur{' a-venir' if not tracabilite['horaire_moyen'] else ''}" style="--accent:{BLEU}">
      <div class="valeur">{horaire_valeur}</div>
      <div class="libelle">Horaire moyen des appels{suffixe_trace}</div>
    </div>
    <div class="compteur{' a-venir' if not tracabilite['repartition_outils'] else ''}" style="--accent:{ROSE}">
      <div class="valeur">{repartition_valeur}</div>
      <div class="libelle">{repartition_libelle}</div>
    </div>
    <div class="compteur{' a-venir' if tracabilite['cout_total_usd'] is None else ''}" style="--accent:{SAUGE}">
      <div class="valeur">{cout_valeur}</div>
      <div class="libelle">Coût total{suffixe_trace} — impact carbone : pas encore de méthode fiable</div>
    </div>
  </div>

  {_bloc_outils(activations)}

  <div class="bandeau-actions">
    <a class="bouton" href="/backoffice/exports/contacts_marketing.csv">⬇ Contacts marketing (CSV)</a>
    <a class="bouton" href="/backoffice/exports/objets_perdus.csv">⬇ Objets perdus (CSV)</a>
    <a class="bouton" href="/backoffice/exports/demandes_rappel.csv">⬇ Demandes de rappel (CSV)</a>
  </div>

  <div class="section">
    <h2>Appels ({len(appels)} affiché{'s' if len(appels) > 1 else ''})</h2>
    {blocs_appels}
  </div>

</main>
</body>
</html>"""
