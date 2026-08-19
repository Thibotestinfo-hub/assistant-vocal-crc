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


def exporter_demandes_rappel():
    return _exporter_csv("demandes_rappel", COLONNES_DEMANDES_RAPPEL)


COLONNES_CONTACTS = ["source", "cree_le", "nom", "telephone", "email", "opt_in_marketing"]


def exporter_contacts_marketing():
    """Combine les coordonnées collectées dans les deux tables (objets
    perdus, demandes de rappel) en un seul export, avec leur consentement
    marketing — c'est ce que l'équipe CRC réutilise réellement, pas les
    objets perdus en tant que tels. Toutes les lignes sont incluses (avec
    ou sans consentement) : le filtre sur opt_in_marketing se fait à la
    lecture du CSV, pas à l'export, pour ne rien perdre par erreur."""
    conn = connexion_app()
    lignes = []
    for table in ("objets_perdus", "demandes_rappel"):
        for l in conn.execute(
            f"SELECT cree_le, nom, telephone, email, opt_in_marketing FROM {table} ORDER BY id"
        ).fetchall():
            lignes.append([table] + [l[c] for c in ("cree_le", "nom", "telephone", "email", "opt_in_marketing")])
    conn.close()

    tampon = io.StringIO()
    ecrivain = csv.writer(tampon, delimiter=";")
    ecrivain.writerow(COLONNES_CONTACTS)
    ecrivain.writerows(lignes)
    return tampon.getvalue()
