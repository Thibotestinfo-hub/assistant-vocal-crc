"""
Exports CSV — Étape 6, point 2 de la méthode : "Objets perdus, demandes
de rappel, contacts collectés avec leurs consentements. En CSV."

Un export par table, colonnes dans l'ordre du schéma (voir
assistant/outils/db.py). opt_in_marketing est toujours inclus : c'est
justement le consentement que ces exports doivent tracer.
"""

import csv
import io

from assistant.outils.db import connexion_app

COLONNES_OBJETS_PERDUS = [
    "id", "cree_le", "nature", "description", "ligne", "sens",
    "date_perte", "creneau_horaire", "lieu", "arret_id",
    "nom", "telephone", "email", "opt_in_marketing",
]

COLONNES_DEMANDES_RAPPEL = [
    "id", "cree_le", "telephone", "nom", "email", "motif", "resume", "opt_in_marketing",
]


def _exporter_csv(table, colonnes):
    conn = connexion_app()
    lignes = conn.execute(f"SELECT {', '.join(colonnes)} FROM {table} ORDER BY id").fetchall()
    conn.close()

    tampon = io.StringIO()
    ecrivain = csv.writer(tampon, delimiter=";")
    ecrivain.writerow(colonnes)
    for ligne in lignes:
        ecrivain.writerow([ligne[c] for c in colonnes])
    return tampon.getvalue()


def exporter_objets_perdus():
    return _exporter_csv("objets_perdus", COLONNES_OBJETS_PERDUS)


def supprimer_objet_perdu(declaration_id):
    """Pas d'usage courant prévu (une vraie déclaration ne devrait jamais
    être supprimée) — sert au nettoyage d'entrées de test ou d'un faux
    appel d'outil par le modèle (voir docs/prochaines-etapes.md, bug
    enregistrer_satisfaction du 28/08/2026)."""
    conn = connexion_app()
    conn.execute("DELETE FROM objets_perdus WHERE id = ?", (declaration_id,))
    conn.commit()
    conn.close()


def exporter_demandes_rappel():
    return _exporter_csv("demandes_rappel", COLONNES_DEMANDES_RAPPEL)


def lister_demandes_rappel(limite=200):
    """Pour l'affichage direct dans le back-office (Suivi) : les demandes
    de rappel les plus récentes, avec leur consentement marketing. Colonnes
    volontairement réduites par rapport à l'export CSV complet (pas de
    resume/email affichés ici) — l'export CSV reste la source complète."""
    conn = connexion_app()
    lignes = conn.execute(
        "SELECT id, cree_le, nom, telephone, motif, opt_in_marketing FROM demandes_rappel "
        "ORDER BY id DESC LIMIT ?",
        (limite,),
    ).fetchall()
    conn.close()
    return [dict(l) for l in lignes]
