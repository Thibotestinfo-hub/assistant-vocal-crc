"""Rendu HTML du back-office — page consolidée en 2 onglets ("Live" /
"Suivi"), sans framework front : un peu de JS pour basculer d'onglet et
pour afficher le détail d'un appel dans le panneau latéral, formulaires
HTML classiques pour les actions.

Structure et disposition reprises fidèlement de la maquette PDF fournie
par l'équipe (25/08/2026, revue le 25/08 après un premier essai trop
éloigné) :
- Live : bouton d'arrêt général en anneau, réglages voix, appels en
  cours (interrogé en direct chez ElevenLabs à chaque affichage, voir
  assistant/elevenlabs_api.py:appels_en_cours), activation des outils
  avec interrupteurs.
- Suivi : indicateurs en tuiles, tableau des appels + panneau de détail
  latéral qui s'ouvre au clic (comme dans la maquette).

Palette de couleurs fournie par l'équipe CRC (Étape 6, retour visuel) :
bleu clair, sauge, rouge, rose. --bleu-fonce est une teinte plus soutenue
de ce même bleu (pas une nouvelle couleur), utilisée pour l'onglet actif
et l'anneau du bouton, comme dans la maquette."""

import html
import json
import time

from assistant.elevenlabs_api import nom_voix, voix_disponibles

BLEU = "#A6D7E4"
BLEU_FONCE = "#2f7288"
SAUGE = "#C7DFD4"
ROUGE = "#FF6666"
ROSE = "#FFB6C8"

_NOMS_LISIBLES = {
    "rechercher_arret": "Identifier un arrêt",
    "horaires_theoriques": "Horaires théoriques",
    "rechercher_information": "Questions tarifs / pratique (FAQ)",
    "enregistrer_objet_perdu": "Déclarer un objet perdu",
    "demander_rappel": "Demander à être rappelé",
    "transferer_agent": "Transférer vers un conseiller",
}

_DESCRIPTIONS_OUTILS = {
    "rechercher_arret": "Identifie l'arrêt mentionné par l'appelant (nom, commune, ligne).",
    "horaires_theoriques": "Donne les horaires théoriques des prochains passages à un arrêt.",
    "rechercher_information": "Répond aux questions tarifs et pratiques depuis la base de connaissance.",
    "enregistrer_objet_perdu": "Enregistre une déclaration d'objet perdu.",
    "demander_rappel": "Enregistre une demande de rappel par un conseiller.",
    "transferer_agent": "Bascule l'appel vers un conseiller humain.",
}

_NOMS_MOTIFS = {
    "amende": "Amende",
    "reclamation": "Réclamation",
    "tad": "Transport à la demande",
    "scolaire": "Transport scolaire",
    "hors_perimetre": "Hors périmètre du réseau",
    "demande_agent": "Demande d'agent",
}

_NOMS_SOURCES_APPEL = {
    "twilio": "Appel téléphonique",
    "widget": "Test (widget)",
    "react_sdk": "Test (react_sdk)",
}

_ICONES_COMPTEURS = {
    "appels": "📞",
    "satisfaction": "👍",
    "duree": "⏱",
    "horaire": "🕒",
    "cout": "💶",
}

_STYLE = f"""
:root {{
  --bleu: {BLEU};
  --bleu-fonce: {BLEU_FONCE};
  --sauge: {SAUGE};
  --rouge: {ROUGE};
  --rose: {ROSE};
  --texte: #22303c;
  --texte-doux: #6b7a86;
  --fond: #f4f7f8;
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
  font-size: 16px;
}}
a {{ color: var(--bleu-fonce); }}
header.entete {{
  padding: 1.1rem 3rem 0.9rem;
  border-bottom: 1px solid var(--bordure);
  display: flex;
  align-items: center;
  gap: 0.7rem;
}}
header.entete .logo-mark {{
  color: var(--rouge);
  font-size: 1.5rem;
  line-height: 1;
}}
header.entete .marque {{
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--texte-doux);
  text-transform: uppercase;
  line-height: 1.15;
}}
header.entete h1 {{
  font-size: 1.3rem;
  font-weight: 500;
  margin: 0 0 0 0.6rem;
  color: var(--texte);
}}
header.entete .entete-titres {{ display: flex; align-items: baseline; }}
main {{
  max-width: 100rem;
  margin: 0 auto;
  padding: 1.8rem 3rem;
}}
.onglets {{
  display: flex;
  margin-bottom: 1.8rem;
  max-width: 34rem;
}}
.onglet-btn {{
  font-family: inherit;
  font-size: 1.05rem;
  font-weight: 600;
  padding: 0.9rem 0;
  flex: 1;
  border: none;
  cursor: pointer;
  background: var(--bleu);
  color: #ffffffcc;
}}
.onglet-btn.actif {{
  background: var(--bleu-fonce);
  color: #fff;
}}
.contenu-onglet {{ }}

/* --- Live : power / voix / outils à gauche, appels en cours à droite
   sur toute la hauteur (maquette du 26/08 : l'encart "Appels en cours"
   doit descendre jusqu'au bas de "Outils actifs", qui lui doit s'arrêter
   à la bordure droite de "Paramétrages voix", pas s'étendre en dessous
   de "Appels en cours") --- */
.grille-live-haut {{
  display: grid;
  grid-template-columns: 15rem 1.6fr 1fr;
  grid-template-rows: auto auto;
  gap: 1.6rem;
  margin-bottom: 1.8rem;
}}
.carte-power {{ grid-column: 1; grid-row: 1; }}
.carte-voix {{ grid-column: 2; grid-row: 1; }}
.carte-appels-cours {{ grid-column: 3; grid-row: 1 / span 2; }}
.carte-outils {{ grid-column: 1 / span 2; grid-row: 2; }}
@media (max-width: 900px) {{
  .grille-live-haut {{ grid-template-columns: 1fr; }}
  .carte-power, .carte-voix, .carte-appels-cours, .carte-outils {{
    grid-column: 1; grid-row: auto;
  }}
}}
.carte {{
  background: var(--carte);
  border: 1px solid var(--bordure);
  border-radius: 12px;
  padding: 1.4rem 1.6rem;
}}
.carte h2 {{
  font-size: 1rem;
  margin: 0 0 1rem;
}}
.carte h2 em {{ font-style: italic; font-weight: 400; color: var(--texte-doux); }}
.carte-power {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 1.1rem;
}}
.carte-power form {{ margin: 0; }}
.anneau-power {{
  width: 7.5rem;
  height: 7.5rem;
  border-radius: 50%;
  border: 6px solid var(--bleu);
  background: #eef7fa;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}}
.anneau-power .icone-power {{ font-size: 2.4rem; color: var(--bleu-fonce); }}
.anneau-power.coupe {{ border-color: var(--rouge); background: {ROUGE}11; }}
.anneau-power.coupe .icone-power {{ color: var(--rouge); }}
.legende-power {{ font-size: 0.9rem; margin: 0; }}
.voix-form {{
  display: flex;
  gap: 0.6rem;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}}
.voix-form select {{
  font-family: inherit;
  font-size: 0.9rem;
  padding: 0.55rem 0.8rem;
  border-radius: 7px;
  border: 1px solid var(--bordure);
  background: #eef1f3;
  flex: 1;
  min-width: 10rem;
}}
.bouton-icone {{
  padding: 0.55rem 0.7rem;
  font-size: 1rem;
  line-height: 1;
  flex-shrink: 0;
}}
.champ-label {{
  display: block;
  font-style: italic;
  color: var(--texte-doux);
  font-size: 0.85rem;
  margin: 0.9rem 0 0.3rem;
}}
.curseur {{
  width: 100%;
  accent-color: var(--sauge);
}}
.voix-form-complete {{ margin: 0; }}
.note-a-venir {{
  color: var(--texte-doux);
  font-size: 0.78rem;
  font-style: italic;
  margin: 0.9rem 0 0;
}}
.erreur-voix {{ color: var(--rouge); font-size: 0.82rem; margin-top: 0.6rem; }}
.carte-appels-cours {{ display: flex; flex-direction: column; }}
.a-venir-message {{
  color: var(--texte-doux);
  font-size: 0.85rem;
  font-style: italic;
  margin: 0;
}}
.ligne-appel-en-cours {{
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--bordure);
  font-size: 0.88rem;
}}
.ligne-appel-en-cours:last-child {{ border-bottom: none; }}

/* --- Live : grille des outils --- */
.outils-grille {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}}
@media (max-width: 900px) {{
  .outils-grille {{ grid-template-columns: 1fr; }}
}}
.outil {{
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.5rem 0;
  font-size: 0.95rem;
}}
.etiquette-outil {{ display: flex; align-items: center; }}
.info-icone {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.05rem;
  height: 1.05rem;
  border-radius: 50%;
  background: #d7dbdf;
  color: #5b6570;
  font-size: 0.68rem;
  font-style: italic;
  margin-left: 0.4rem;
  cursor: help;
  flex-shrink: 0;
}}
.outil form {{ margin: 0; }}
.interrupteur-outil {{
  width: 3.5rem;
  height: 1.7rem;
  border-radius: 999px;
  border: none;
  cursor: pointer;
  position: relative;
  padding: 0;
  flex-shrink: 0;
}}
.interrupteur-outil.on {{ background: #4a9d76; }}
.interrupteur-outil.off {{ background: #c7ccd1; }}
.bille-interrupteur {{
  position: absolute;
  top: 0.16rem;
  width: 1.38rem;
  height: 1.38rem;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0,0,0,.25);
  transition: left .15s;
}}
.interrupteur-outil.on .bille-interrupteur {{ left: calc(100% - 1.54rem); }}
.interrupteur-outil.off .bille-interrupteur {{ left: 0.16rem; }}

/* --- Suivi : tuiles d'indicateurs (picto à gauche, chiffre à droite en
   plus gros, 3 par ligne) + répartition en anneau à côté --- */
.section-indicateurs {{
  display: flex;
  gap: 1.5rem;
  margin-bottom: 1.8rem;
  align-items: stretch;
}}
@media (max-width: 1100px) {{
  .section-indicateurs {{ flex-direction: column; }}
}}
.grille-compteurs {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  flex: 3;
}}
@media (max-width: 700px) {{
  .grille-compteurs {{ grid-template-columns: repeat(2, 1fr); }}
}}
.compteur {{
  background: var(--carte);
  border: 1px solid var(--bordure);
  border-top: 4px solid var(--accent, var(--bleu));
  border-radius: 12px;
  padding: 1.2rem 1.3rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}}
.compteur .icone-compteur {{ font-size: 2.3rem; flex-shrink: 0; }}
.compteur .compteur-corps {{ display: flex; flex-direction: column; }}
.compteur .valeur {{ font-size: 2.1rem; font-weight: 700; line-height: 1.1; }}
.compteur .libelle {{ color: var(--texte-doux); font-size: 0.78rem; margin-top: 0.2rem; }}
.compteur.a-venir {{ opacity: 0.55; }}
.compteur.a-venir .valeur {{ font-size: 1.05rem; font-weight: 500; }}
.carte-repartition {{
  flex: 1.3;
  display: flex;
  flex-direction: column;
}}
.donut-bloc {{ display: flex; align-items: center; gap: 1.2rem; flex: 1; }}
.donut-legende {{ font-size: 0.82rem; }}
.legende-item {{ display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem; }}
.pastille-legende {{
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}}

.bandeau-actions {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin-bottom: 1.5rem;
}}
.bouton, button {{
  font-family: inherit;
  font-size: 0.88rem;
  padding: 0.55rem 1.1rem;
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
.bouton-grand {{ font-size: 1rem; padding: 0.75rem 1.5rem; font-weight: 700; }}
.bandeau-actions button, .bandeau-actions .bouton {{ background: {BLEU}33; border-color: {BLEU}88; font-weight: 500; }}
button[name="qualite"][value="bonne"] {{ background: {SAUGE}77; border-color: {SAUGE}; }}
button[name="qualite"][value="mauvaise"] {{ background: {ROUGE}22; border-color: {ROUGE}77; }}

/* --- Suivi : tableau pleine largeur + panneau de détail en dessous,
   qui s'ouvre au clic sur l'œil (les deux tables — appels et demandes
   de rappel — ont ainsi la même largeur, voir maquette du 26/08) --- */
.carte-tableau {{ padding: 0; overflow-x: auto; margin-bottom: 1.5rem; }}
.carte-tableau table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
.carte-tableau th {{
  text-align: left;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--texte-doux);
  padding: 1rem 1rem 0.7rem;
  border-bottom: 1px solid var(--bordure);
  white-space: nowrap;
}}
.carte-tableau td {{
  padding: 0.7rem 1rem;
  border-bottom: 1px solid var(--bordure);
  vertical-align: middle;
  white-space: nowrap;
}}
.carte-tableau tr:last-child td {{ border-bottom: none; }}
.carte-tableau td.col-motif-table {{ white-space: normal; }}
.bouton-voir {{
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.05rem;
  padding: 0.2rem 0.4rem;
}}
.bouton-voir.actif {{ background: {BLEU}44; border-radius: 6px; }}
.carte-detail-appel {{ margin-bottom: 1.5rem; position: relative; }}
.bouton-fermer-detail {{
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: none;
  border: none;
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
  color: var(--texte-doux);
  padding: 0.3rem;
}}
.transcription {{
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  margin-bottom: 1rem;
}}
.tour-transcription {{
  padding: 0.6rem 0.9rem;
  border-radius: 10px;
  max-width: 80%;
  font-size: 0.88rem;
}}
.tour-transcription.role-user {{ background: {BLEU}22; align-self: flex-start; }}
.tour-transcription.role-agent {{ background: {SAUGE}44; align-self: flex-end; }}
.role-transcription {{
  display: block;
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--texte-doux);
  margin-bottom: 0.2rem;
}}
.tour-transcription p {{ margin: 0; }}
.outils-tour {{ font-size: 0.78rem; color: var(--texte-doux); font-style: italic; margin-top: 0.3rem !important; }}
.detail-appel-contenu pre {{
  background: var(--fond);
  padding: 0.9rem;
  border-radius: 6px;
  overflow-x: auto;
  white-space: pre-wrap;
  font-size: 0.76rem;
  max-height: 18rem;
  overflow-y: auto;
}}
.detail-appel-contenu textarea {{
  width: 100%;
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


def _motif_appel(outils_utilises):
    if not outils_utilises:
        return "—"
    outils = json.loads(outils_utilises)
    if not outils:
        return "—"
    return ", ".join(_NOMS_LISIBLES.get(o, o) for o in outils)


def _voix_appel(voix_utilisees):
    if not voix_utilisees:
        return "—"
    voix = json.loads(voix_utilisees)
    if not voix:
        return "—"
    return ", ".join(nom_voix(v) for v in voix)


def _ligne_tableau_appel(a, numero):
    date, _, heure = (a["cree_le"] or "").partition("T")
    return f"""<tr>
  <td>{numero}</td>
  <td>{html.escape(_voix_appel(a.get('voix_utilisees')))}</td>
  <td>{html.escape(date)}</td>
  <td>{html.escape(heure)}</td>
  <td>{_formater_duree(a.get('duree_secs'))}</td>
  <td class="col-motif-table">{html.escape(_motif_appel(a.get('outils_utilises')))}</td>
  <td><button type="button" class="bouton-voir" id="bouton-voir-{a['id']}" onclick="afficherDetail({a['id']})" title="Voir le détail">👁</button></td>
</tr>"""


_NOMS_ROLES = {"user": "Appelant", "agent": "Assistant"}


def _transcription_appel(donnees):
    """Rendu lisible du transcript (qui a dit quoi), pas seulement la
    charge brute. Champs role/message : documentés par ElevenLabs pour
    le webhook post_call_transcription — pas encore reconfirmés sur un
    payload réel complet depuis cet environnement (celui utilisé pour
    les tests locaux est un extrait fabriqué à la main, sans champ
    message). À vérifier sur un vrai appel avant de considérer ce rendu
    fiable à 100 %."""
    tours = donnees.get("transcript") or []
    blocs = []
    for tour in tours:
        role_brut = tour.get("role")
        role = _NOMS_ROLES.get(role_brut, role_brut or "—")
        message = (tour.get("message") or "").strip()
        outils = [tc.get("tool_name") for tc in (tour.get("tool_calls") or []) if tc.get("tool_name")]
        if not message and not outils:
            continue
        bloc_message = f"<p>{html.escape(message)}</p>" if message else ""
        bloc_outils = (
            f'<p class="outils-tour">🛠 {html.escape(", ".join(_NOMS_LISIBLES.get(o, o) for o in outils))}</p>'
            if outils else ""
        )
        classe = "role-agent" if role_brut == "agent" else "role-user"
        blocs.append(f"""<div class="tour-transcription {classe}">
  <span class="role-transcription">{html.escape(role)}</span>
  {bloc_message}
  {bloc_outils}
</div>""")
    if not blocs:
        return '<p class="a-venir-message">Pas de transcription disponible pour cet appel.</p>'
    return f'<div class="transcription">{"".join(blocs)}</div>'


def _detail_appel(a):
    charge_brute = json.loads(a["donnees_brutes"])
    donnees = charge_brute.get("data", charge_brute) if isinstance(charge_brute, dict) else {}
    donnees_brutes = json.dumps(charge_brute, ensure_ascii=False, indent=2)
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

    return f"""<div class="detail-appel-contenu" id="detail-{a['id']}" style="display:none">
  <h3 style="font-size:0.95rem;margin:0 0 0.3rem">Appel {html.escape(a['conversation_id'] or '—')}</h3>
  <p style="font-size:0.8rem;color:var(--texte-doux);margin:0 0 1rem">{html.escape(a['cree_le'])} — {html.escape(a['statut'] or '—')}</p>
  <h4 style="font-size:0.85rem;margin:0 0 0.5rem">Évaluer cet appel</h4>
  <form method="post" action="/backoffice/appels/{a['id']}/evaluer">
    <textarea name="note" placeholder="Note libre, optionnelle : ce qui n'allait pas, la question posée, la réponse attendue..."></textarea>
    <div style="margin-top:0.5rem">
      <button type="submit" name="qualite" value="bonne">👍 Bonne réponse</button>
      <button type="submit" name="qualite" value="mauvaise">👎 Mauvaise réponse</button>
    </div>
  </form>
  {bloc_evaluations}
  <h4 style="font-size:0.85rem;margin:1rem 0 0.5rem">Transcription de la conversation</h4>
  {_transcription_appel(donnees)}
  <h4 style="font-size:0.85rem;margin:1rem 0 0.5rem">Charge brute reçue du webhook</h4>
  <pre>{html.escape(donnees_brutes)}</pre>
</div>"""


def _carte_power(activations):
    tous_actif = activations["tous"]
    return f"""<div class="carte carte-power">
  <form method="post" action="/backoffice/activation/tous/basculer">
    <button type="submit" class="anneau-power {'coupe' if not tous_actif else ''}" title="{'Tout arrêter' if tous_actif else 'Tout relancer'}">
      <span class="icone-power">⏻</span>
    </button>
  </form>
  <p class="legende-power">Assistant conversationnel <strong>{"actif" if tous_actif else "à l'arrêt"}</strong></p>
</div>"""


def _carte_voix(erreur_voix):
    options = "".join(
        f'<option value="{html.escape(v["id"])}">{html.escape(v["nom"])}</option>'
        for v in voix_disponibles()
    )
    erreur_html = (
        '<p class="erreur-voix">Le changement a échoué (ElevenLabs indisponible '
        "ou clé API manquante). Réessayez dans un instant.</p>"
        if erreur_voix else ""
    )
    return f"""<div class="carte carte-voix">
  <h2>Paramétrages <em>voix</em></h2>
  <form class="voix-form-complete" method="post" action="/backoffice/voix/changer">
    <div class="voix-form">
      <select name="voice_id" id="select-voix">
        <option value="" selected>Ne pas changer la voix</option>
        {options}
      </select>
      <button type="button" class="bouton-icone" onclick="ecouterVoix()" title="Écouter cette voix">🔊</button>
    </div>
    <label class="champ-label">ton <span class="info-icone" title="Stabilité de la voix ElevenLabs (stability) : plus haut = plus régulier, plus bas = plus de variation.">i</span></label>
    <input type="range" name="ton" min="0" max="1" step="0.05" value="0.5" class="curseur">
    <label class="champ-label">autre <span class="info-icone" title="Style ElevenLabs (style) : plus haut = plus expressif.">i</span></label>
    <input type="range" name="autre" min="0" max="1" step="0.05" value="0" class="curseur">
    <button type="submit" class="bouton accent" style="margin-top:1rem">Appliquer</button>
  </form>
  <audio id="lecteur-voix" style="display:none"></audio>
  {erreur_html}
  <p class="note-a-venir">Les curseurs repartent d'une valeur par défaut à chaque affichage — cette page n'interroge pas ElevenLabs pour connaître le réglage en cours (pour rester rapide et indépendante).</p>
</div>"""


def _ligne_tableau_demande(d):
    date, _, heure = (d["cree_le"] or "").partition("T")
    opt_in = "Oui" if d["opt_in_marketing"] else "Non"
    return f"""<tr>
  <td>{html.escape(d['nom'] or '—')}</td>
  <td>{html.escape(d['telephone'] or '—')}</td>
  <td>{html.escape(date)} {html.escape(heure)}</td>
  <td>{html.escape(_NOMS_MOTIFS.get(d['motif'], d['motif'] or '—'))}</td>
  <td>{opt_in}</td>
</tr>"""


def _carte_demandes_rappel(demandes):
    lignes = (
        "\n".join(_ligne_tableau_demande(d) for d in demandes)
        if demandes else '<tr><td colspan="5">Aucune demande pour l\'instant.</td></tr>'
    )
    return f"""<div class="carte carte-tableau" style="margin-bottom:1.5rem">
  <div style="display:flex;justify-content:space-between;align-items:center;padding:1rem 1rem 0">
    <h2 style="margin:0">Demandes de rappel ({len(demandes)})</h2>
    <a class="bouton accent bouton-grand" href="/backoffice/exports/demandes_rappel.csv">⬇ Télécharger (CSV)</a>
  </div>
  <table>
    <thead>
      <tr>
        <th>Nom</th>
        <th>Téléphone</th>
        <th>Heure d'appel</th>
        <th>Motif</th>
        <th>Opt-in marketing</th>
      </tr>
    </thead>
    <tbody>
      {lignes}
    </tbody>
  </table>
</div>"""


def _ligne_appel_en_cours(c):
    source = _NOMS_SOURCES_APPEL.get(c.get("conversation_initiation_source"), c.get("conversation_initiation_source") or "—")
    debut = c.get("start_time_unix_secs")
    duree = _formater_duree(int(time.time()) - debut) if debut else "à l'instant"
    return f"""<div class="ligne-appel-en-cours">
  <span>{html.escape(source)}</span>
  <span>{duree}</span>
</div>"""


def _carte_appels_en_cours(en_cours):
    if en_cours is None:
        contenu = '<p class="a-venir-message">ElevenLabs indisponible ou trop lent pour l\'instant — réessayez en rechargeant la page.</p>'
    elif not en_cours:
        contenu = '<p class="a-venir-message">Aucun appel en cours.</p>'
    else:
        contenu = "\n".join(_ligne_appel_en_cours(c) for c in en_cours)
    return f"""<div class="carte carte-appels-cours">
  <h2>Appels en cours</h2>
  {contenu}
</div>"""


def _grille_outils(activations):
    def _ligne(cle, libelle):
        actif = activations["outils"][cle]
        classe = "on" if actif else "off"
        description = _DESCRIPTIONS_OUTILS.get(cle, "")
        return f"""<div class="outil">
  <span class="etiquette-outil">{html.escape(libelle)}<span class="info-icone" title="{html.escape(description)}">i</span></span>
  <form method="post" action="/backoffice/activation/{cle}/basculer">
    <button type="submit" class="interrupteur-outil {classe}" title="{'Désactiver' if actif else 'Activer'}">
      <span class="bille-interrupteur"></span>
    </button>
  </form>
</div>"""

    return "".join(_ligne(cle, libelle) for cle, libelle in _NOMS_LISIBLES.items())


def _formater_duree(secs):
    if secs is None:
        return "à venir"
    m, s = divmod(secs, 60)
    return f"{m} min {s:02d}" if m else f"{s} s"


_COULEURS_REPARTITION = [BLEU_FONCE, SAUGE, ROSE, ROUGE, BLEU, "#8fb9c9"]


def _svg_repartition(repartition):
    """Diagramme en anneau (donut) dessiné à la main en SVG — pas de
    librairie de graphiques, cohérent avec "pas de framework front" :
    un cercle par catégorie, découpé via stroke-dasharray."""
    r = 45
    if not repartition:
        return (
            '<svg viewBox="0 0 120 120" width="110" height="110" role="img" aria-label="Aucune donnée">'
            f'<circle cx="60" cy="60" r="{r}" fill="none" stroke="#e6ebee" stroke-width="18"/></svg>'
        )
    total = sum(repartition.values())
    circonference = 2 * 3.14159265 * r
    segments = []
    decalage = 0.0
    for i, (outil, n) in enumerate(sorted(repartition.items(), key=lambda kv: -kv[1])):
        longueur = (n / total) * circonference
        couleur = _COULEURS_REPARTITION[i % len(_COULEURS_REPARTITION)]
        segments.append(
            f'<circle cx="60" cy="60" r="{r}" fill="none" stroke="{couleur}" stroke-width="18" '
            f'stroke-dasharray="{longueur:.2f} {circonference - longueur:.2f}" '
            f'stroke-dashoffset="{-decalage:.2f}" transform="rotate(-90 60 60)"/>'
        )
        decalage += longueur
    return f'<svg viewBox="0 0 120 120" width="110" height="110" role="img" aria-label="Répartition des appels par motif">{"".join(segments)}</svg>'


def _legende_repartition(repartition):
    if not repartition:
        return '<p class="a-venir-message">Pas encore de données.</p>'
    items = sorted(repartition.items(), key=lambda kv: -kv[1])
    return "".join(
        f'<div class="legende-item"><span class="pastille-legende" '
        f'style="background:{_COULEURS_REPARTITION[i % len(_COULEURS_REPARTITION)]}"></span>'
        f'{html.escape(_NOMS_LISIBLES.get(outil, outil))} — {n}</div>'
        for i, (outil, n) in enumerate(items)
    )


def _carte_repartition(repartition, suffixe_trace):
    return f"""<div class="carte carte-repartition">
  <h2>Répartition des appels par motif{suffixe_trace}</h2>
  <div class="donut-bloc">
    {_svg_repartition(repartition)}
    <div class="donut-legende">{_legende_repartition(repartition)}</div>
  </div>
</div>"""


def page_backoffice(appels, activations, nb_appels, satisfaction, tracabilite, demandes_rappel, en_cours, erreur_voix=False):
    bonnes, total_eval = satisfaction
    if total_eval:
        pct = f"{round(100 * bonnes / total_eval)}%"
        libelle_satisfaction = f"{bonnes}/{total_eval} évaluations"
    else:
        pct = "—"
        libelle_satisfaction = "aucune évaluation pour l'instant"

    duree_valeur = _formater_duree(tracabilite["duree_moyenne_secs"])
    horaire_valeur = tracabilite["horaire_moyen"] or "à venir"
    cout_valeur = f"{tracabilite['cout_total_usd']:.3f} $" if tracabilite["cout_total_usd"] is not None else "à venir"
    n_trace = tracabilite["nb_avec_tracabilite"]
    suffixe_trace = f" — sur {n_trace} appel{'s' if n_trace > 1 else ''}" if n_trace else ""

    lignes_tableau = (
        "\n".join(_ligne_tableau_appel(a, i) for i, a in enumerate(appels, 1))
        if appels else '<tr><td colspan="7">Aucun appel pour l\'instant.</td></tr>'
    )
    details_appels = "\n".join(_detail_appel(a) for a in appels)

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Back-office — Assistant vocal CRC, zone Étang</title>
<style>{_STYLE}</style>
</head>
<body>
<header class="entete">
  <span class="logo-mark">➜</span>
  <div>
    <div class="marque">Assistant vocal · zone Étang</div>
  </div>
  <div class="entete-titres">
    <h1>Assistant conversationnel — Expérimentation 2026</h1>
  </div>
</header>
<main>

  <div class="onglets">
    <button type="button" class="onglet-btn actif" data-cible="live" onclick="afficherOnglet('live')">Live</button>
    <button type="button" class="onglet-btn" data-cible="suivi" onclick="afficherOnglet('suivi')">Suivi</button>
  </div>

  <div id="onglet-live" class="contenu-onglet">
    <div class="grille-live-haut">
      {_carte_power(activations)}
      {_carte_voix(erreur_voix)}
      {_carte_appels_en_cours(en_cours)}
      <div class="carte carte-outils">
        <h2>Outils actifs</h2>
        <div class="outils-grille">
          {_grille_outils(activations)}
        </div>
      </div>
    </div>
  </div>

  <div id="onglet-suivi" class="contenu-onglet" style="display:none">

    <div class="section-indicateurs">
      <div class="grille-compteurs">
        <div class="compteur" style="--accent:{BLEU}">
          <div class="icone-compteur">{_ICONES_COMPTEURS['appels']}</div>
          <div class="compteur-corps">
            <div class="valeur">{nb_appels}</div>
            <div class="libelle">Appels captés</div>
          </div>
        </div>
        <div class="compteur" style="--accent:{ROSE}">
          <div class="icone-compteur">{_ICONES_COMPTEURS['satisfaction']}</div>
          <div class="compteur-corps">
            <div class="valeur">{pct}</div>
            <div class="libelle">Satisfaction — {libelle_satisfaction}</div>
          </div>
        </div>
        <div class="compteur{' a-venir' if tracabilite['duree_moyenne_secs'] is None else ''}" style="--accent:{SAUGE}">
          <div class="icone-compteur">{_ICONES_COMPTEURS['duree']}</div>
          <div class="compteur-corps">
            <div class="valeur">{duree_valeur}</div>
            <div class="libelle">Durée moyenne d'appel{suffixe_trace}</div>
          </div>
        </div>
        <div class="compteur{' a-venir' if not tracabilite['horaire_moyen'] else ''}" style="--accent:{BLEU}">
          <div class="icone-compteur">{_ICONES_COMPTEURS['horaire']}</div>
          <div class="compteur-corps">
            <div class="valeur">{horaire_valeur}</div>
            <div class="libelle">Horaire moyen des appels{suffixe_trace}</div>
          </div>
        </div>
        <div class="compteur{' a-venir' if tracabilite['cout_total_usd'] is None else ''}" style="--accent:{SAUGE}">
          <div class="icone-compteur">{_ICONES_COMPTEURS['cout']}</div>
          <div class="compteur-corps">
            <div class="valeur">{cout_valeur}</div>
            <div class="libelle">Coût total{suffixe_trace} — impact carbone : pas encore de méthode fiable</div>
          </div>
        </div>
      </div>
      {_carte_repartition(tracabilite['repartition_outils'], suffixe_trace)}
    </div>

    <div class="bandeau-actions">
      <a class="bouton" href="/backoffice/exports/objets_perdus.csv">⬇ Objets perdus (CSV)</a>
      <form method="post" action="/backoffice/appels/retraiter-tracabilite" style="display:inline">
        <button type="submit" class="bouton" title="Recalcule durée/coût/modèles pour les appels déjà reçus mais enregistrés avant ce chantier">↻ Recalculer la traçabilité</button>
      </form>
    </div>

    <div class="carte carte-tableau">
      <table>
        <thead>
          <tr>
            <th>Call #</th>
            <th>Voix</th>
            <th>Jour</th>
            <th>Heure</th>
            <th>Durée</th>
            <th>Motif</th>
            <th>Voir</th>
          </tr>
        </thead>
        <tbody>
          {lignes_tableau}
        </tbody>
      </table>
    </div>

    <div class="carte carte-detail-appel" id="panneau-detail" style="display:none">
      <button type="button" class="bouton-fermer-detail" onclick="fermerDetail()" title="Fermer">✕</button>
      {details_appels}
    </div>

    {_carte_demandes_rappel(demandes_rappel)}

  </div>

</main>
<script>
function ecouterVoix() {{
  var select = document.getElementById('select-voix');
  var voiceId = select.value;
  if (!voiceId) {{
    alert("Choisissez d'abord une voix dans la liste.");
    return;
  }}
  var lecteur = document.getElementById('lecteur-voix');
  lecteur.onerror = function() {{
    alert('Impossible de lire cet extrait pour le moment (ElevenLabs indisponible ?).');
  }};
  lecteur.src = '/backoffice/voix/' + voiceId + '/apercu';
  lecteur.play().catch(function() {{
    alert('Impossible de lire cet extrait pour le moment (ElevenLabs indisponible ?).');
  }});
}}
function afficherOnglet(nom) {{
  document.querySelectorAll('.contenu-onglet').forEach(function(el) {{
    el.style.display = (el.id === 'onglet-' + nom) ? '' : 'none';
  }});
  document.querySelectorAll('.onglet-btn').forEach(function(b) {{
    b.classList.toggle('actif', b.dataset.cible === nom);
  }});
}}
function afficherDetail(id) {{
  document.querySelectorAll('.detail-appel-contenu').forEach(function(el) {{
    el.style.display = 'none';
  }});
  document.querySelectorAll('.bouton-voir').forEach(function(b) {{
    b.classList.remove('actif');
  }});
  var panneau = document.getElementById('panneau-detail');
  var cible = document.getElementById('detail-' + id);
  if (cible) {{
    cible.style.display = '';
    panneau.style.display = '';
    panneau.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
  }}
  var bouton = document.getElementById('bouton-voir-' + id);
  if (bouton) bouton.classList.add('actif');
}}
function fermerDetail() {{
  document.getElementById('panneau-detail').style.display = 'none';
  document.querySelectorAll('.bouton-voir').forEach(function(b) {{
    b.classList.remove('actif');
  }});
}}
document.addEventListener('DOMContentLoaded', function() {{
  if (location.hash === '#suivi' || location.hash.indexOf('#appel-') === 0) {{
    afficherOnglet('suivi');
    var id = location.hash.indexOf('#appel-') === 0 ? location.hash.slice(7) : null;
    if (id) afficherDetail(id);
  }}
}});
</script>
</body>
</html>"""
