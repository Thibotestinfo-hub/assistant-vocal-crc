"""
Page publique d'information — /informations, sans authentification.

À la différence du back-office (assistant/backoffice/page.py, réservé à
l'équipe), cette page s'adresse à un appelant ou à un passant : elle
explique le POC et répond aux questions obligatoires d'une information
claire (objectif, données collectées, proportionnalité, droits). Même
parti que le reste du projet : pas de framework front, HTML + CSS en
dur dans une fonction Python.

Règle suivie strictement ici (CLAUDE.md, exactitude) : la page n'affiche
jamais une durée de conservation ou un contact qui ne serait pas
réellement vrai. Les points encore non tranchés au moment d'écrire cette
page (durée de rétention des objets perdus / demandes de rappel / SMS,
voir docs/audit-dsi.md Partie 6.4 et 5.5 recommandation 3) sont signalés
comme tels à l'écran — un repère visuel jaune, pas une valeur inventée —
plutôt que remplis d'un nombre plausible.
"""

from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parent.parent
CONFIG_PATH = RACINE / "data" / "config.yaml"

BLEU_FONCE = "#2f7288"
SAUGE = "#C7DFD4"

_A_COMPLETER = (
    '<span style="background:#fff3b0;padding:2px 6px;border-radius:3px;">'
    "{texte}</span>"
)


def _config():
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def _contact_dpo():
    """Lu depuis data/config.yaml (contact_dpo_email) — jamais en dur
    dans le code, puisque propre à ce réseau (CLAUDE.md, paramétrage)."""
    valeur = _config().get("contact_dpo_email", "")
    if not valeur or valeur.startswith("dpo-exemple"):
        return None
    return valeur


def _reseau_nom():
    return _config().get("nom_reseau_public", "TABM — zone Étang de Berre")


def page_informations():
    contact = _contact_dpo()
    reseau = _reseau_nom()

    if contact:
        bloc_contact = (
            f'<a href="mailto:{contact}?subject=Droit%20RGPD%20-%20assistant%20vocal"'
            f' style="color:{BLEU_FONCE};font-weight:600;">{contact}</a>'
        )
    else:
        bloc_contact = _A_COMPLETER.format(
            texte="adresse de contact du DPO à renseigner avant toute ouverture publique "
            "— voir data/config.yaml, contact_dpo_email"
        )

    duree_objets_sms = _A_COMPLETER.format(
        texte="durée encore en cours de décision pour ces trois cas précis"
    )

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Assistant vocal {reseau} — informations</title>
<style>
  body {{
    font-family: -apple-system, Segoe UI, Roboto, sans-serif;
    max-width: 760px; margin: 0 auto; padding: 24px 20px 60px;
    line-height: 1.55; color: #1c1c1c; background: #fff;
  }}
  h1 {{ color: {BLEU_FONCE}; font-size: 1.5rem; }}
  h2 {{ color: {BLEU_FONCE}; font-size: 1.15rem; margin-top: 2.2em;
        border-bottom: 2px solid {SAUGE}; padding-bottom: 4px; }}
  .chapeau {{ background: {SAUGE}; border-radius: 8px; padding: 14px 18px;
              font-size: 0.95rem; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 0.92rem; }}
  th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid #e3e3e3; vertical-align: top; }}
  th {{ color: {BLEU_FONCE}; }}
  .encadre {{ border: 1px solid {SAUGE}; border-radius: 8px; padding: 16px 18px; margin: 16px 0; }}
  footer {{ margin-top: 3em; font-size: 0.8rem; color: #777; }}
</style>
</head>
<body>

<h1>L'assistant téléphonique {reseau}</h1>

<div class="chapeau">
  Vous venez d'appeler, ou vous allez appeler, un numéro répondu par un
  assistant automatique. Cette page explique ce qu'il fait, quelles
  informations il enregistre, et comment faire valoir vos droits sur
  ces informations.
</div>

<h2>De quoi s'agit-il ?</h2>
<p>
  Il s'agit d'une expérimentation (un « POC », projet pilote) du réseau
  de bus {reseau}. L'objectif est de tester si un assistant vocal
  automatique peut répondre à des questions simples — horaires
  théoriques, tarifs, informations pratiques — et recueillir une
  déclaration d'objet perdu ou une demande de rappel, en complément de
  l'équipe du centre de relation client (CRC), pas à sa place.
</p>
<p>
  Ce n'est pas une intelligence artificielle « généraliste » : elle ne
  répond que sur ce périmètre, à partir d'informations vérifiées du
  réseau, jamais en inventant une réponse. Si elle ne sait pas, elle le
  dit et vous oriente vers un conseiller.
</p>

<h2>Pourquoi vous demande-t-on parfois votre numéro ou votre nom ?</h2>
<p>
  Uniquement quand c'est nécessaire pour vous rendre un service que vous
  avez demandé vous-même :
</p>
<table>
  <tr><th>Vous demandez…</th><th>On vous demande…</th><th>Pour…</th></tr>
  <tr><td>à recevoir un itinéraire par SMS</td><td>votre numéro (nom/prénom facultatifs)</td><td>vous l'envoyer par ce canal</td></tr>
  <tr><td>à déclarer un objet perdu</td><td>une description, votre nom et votre numéro</td><td>qu'un conseiller vous recontacte si l'objet est retrouvé</td></tr>
  <tr><td>à être rappelé (abonnement, réclamation...)</td><td>votre nom et votre numéro</td><td>qu'un conseiller vous recontacte</td></tr>
</table>
<p>
  Aucune de ces informations n'est demandée avant que le service ne soit
  rendu ou la démarche engagée. Rien n'est utilisé à des fins
  commerciales sans votre accord explicite — une seule question
  facultative vous est posée à ce sujet, jamais reproposée si vous
  déclinez.
</p>

<h2>Que conserve-t-on, et combien de temps ?</h2>
<div class="encadre">
  <p><strong>Chaque appel</strong> : l'enregistrement transcrit en texte
  de la conversation et le numéro appelant sont conservés
  <strong>90 jours</strong>, puis supprimés automatiquement. Seules des
  statistiques qui ne permettent d'identifier personne (durée de
  l'appel, coût technique) sont conservées plus longtemps, pour le suivi
  économique du projet.</p>
  <p><strong>Déclaration d'objet perdu, demande de rappel, SMS
  envoyé</strong> : conservés le temps de traiter votre demande.
  {duree_objets_sms}</p>
</div>
<p>
  L'hébergement des données est européen. Certains prestataires
  techniques utilisés pour faire fonctionner le service (synthèse et
  reconnaissance vocale, envoi de SMS, calcul d'itinéraire en cas de
  trajet complexe) sont des sociétés non européennes ; le cadre exact de
  ces transferts est en cours de vérification avec le délégué à la
  protection des données.
</p>

<h2>Vos droits</h2>
<p>
  Vous pouvez demander à accéder aux informations vous concernant, à les
  faire corriger, ou à les faire supprimer. Pour cela, écrivez à :
</p>
<p style="font-size:1.1rem;">{bloc_contact}</p>
<p>
  en indiquant le numéro de téléphone depuis lequel vous avez appelé (ou
  qui a reçu le SMS) — c'est la seule information qui permette de
  retrouver ce qui vous concerne. Votre demande sera traitée par
  l'équipe du projet dans un délai maximum d'un mois, conformément au
  règlement européen sur la protection des données (RGPD).
</p>
<p>
  Vous pouvez aussi adresser une réclamation à la CNIL
  (<a href="https://www.cnil.fr/fr/plaintes" style="color:{BLEU_FONCE};">cnil.fr/fr/plaintes</a>)
  si vous estimez que vos droits n'ont pas été respectés.
</p>

<footer>
  Assistant vocal {reseau} — démonstrateur en phase d'expérimentation.
</footer>

</body>
</html>"""
