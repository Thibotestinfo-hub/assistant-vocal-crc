"""
Édition du dictionnaire de prononciation depuis le back-office — Étape 6,
levier de paramétrage "sans passer par ElevenLabs" (voir
docs/prochaines-etapes.md, point C).

Les règles ajoutées ici vivent dans data/etat/assistant.db (persistant),
pas dans data/prononciation.pls (remis à neuf à chaque déploiement) : une
règle ajoutée par l'équipe CRC ne doit pas disparaître au prochain
déploiement de code. Elles s'appliquent immédiatement (voir
assistant/ingestion/prononciation.py) à ce que dit rechercher_arret.

Ne synchronise PAS (encore) le dictionnaire de prononciation côté
ElevenLabs lui-même — nécessite l'identifiant de ce dictionnaire, pas
encore récupéré. Une règle ajoutée ici corrige donc la confirmation
d'arrêt (rechercher_arret), pas d'éventuelles autres lectures du nom par
la voix ailleurs dans la conversation.
"""

from datetime import datetime

from assistant.ingestion.prononciation import dictionnaire_fichier
from assistant.outils.db import connexion_app


def ajouter_regle(grapheme, alias):
    grapheme = grapheme.strip()
    alias = alias.strip()
    if not grapheme or not alias:
        return {"succes": False, "erreur": "grapheme et alias sont obligatoires"}
    conn = connexion_app()
    conn.execute(
        "INSERT INTO regles_prononciation (grapheme, alias, cree_le) VALUES (?, ?, ?) "
        "ON CONFLICT(grapheme) DO UPDATE SET alias = excluded.alias, cree_le = excluded.cree_le",
        (grapheme, alias, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()
    return {"succes": True}


def supprimer_regle(grapheme):
    conn = connexion_app()
    conn.execute("DELETE FROM regles_prononciation WHERE grapheme = ?", (grapheme,))
    conn.commit()
    conn.close()


def lister_regles_backoffice():
    """Règles ajoutées depuis le back-office, les plus récentes d'abord."""
    conn = connexion_app()
    lignes = conn.execute(
        "SELECT grapheme, alias, cree_le FROM regles_prononciation ORDER BY cree_le DESC"
    ).fetchall()
    conn.close()
    return [dict(l) for l in lignes]


def lister_regles_fichier():
    """Règles du fichier data/prononciation.pls versionné (relecture
    systématique de l'équipe) — affichées en lecture seule dans le
    back-office, pour qu'on voie tout au même endroit sans dupliquer la
    liste ailleurs."""
    return sorted(dictionnaire_fichier().items())
