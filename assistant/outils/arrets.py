"""
Regroupe les arrêts physiques (un par quai) en "arrêts logiques" : même
nom + même commune. C'est ce regroupement que les outils exposent à
l'agent — un appelant dit "Pinchinades", pas "quai 2 de Pinchinades".

Utilisé par rechercher_arret (pour proposer des candidats) et par
horaires_theoriques (pour interroger tous les quais d'un même arrêt).
"""

import unicodedata

from assistant.ingestion.phonetique import code_phonetique
from assistant.outils.db import connexion_gtfs


def _normaliser(texte):
    forme = unicodedata.normalize("NFD", texte)
    sans_accents = "".join(c for c in forme if unicodedata.category(c) != "Mn")
    return sans_accents.lower().strip()


def charger_arrets_logiques(conn=None):
    """Un dict par (stop_name, commune), avec :
    - stop_id : un stop_id représentatif (le premier quai rencontré)
    - membres : la liste de tous les stop_id de ce groupe (tous les quais)
    - lignes : les route_short_name qui desservent ce groupe
    """
    fermer = conn is None
    conn = conn or connexion_gtfs()

    lignes_par_arret = conn.execute(
        """
        SELECT s.stop_name, s.commune,
               GROUP_CONCAT(DISTINCT s.stop_id) AS stop_ids,
               GROUP_CONCAT(DISTINCT r.route_short_name) AS lignes
        FROM stops s
        JOIN stop_times st ON st.stop_id = s.stop_id
        JOIN trips t ON t.trip_id = st.trip_id
        JOIN routes r ON r.route_id = t.route_id
        WHERE s.location_type = 0
        GROUP BY s.stop_name, s.commune
        """
    ).fetchall()

    arrets = []
    for row in lignes_par_arret:
        membres = row["stop_ids"].split(",")
        arrets.append({
            "stop_id": membres[0],
            "stop_name": row["stop_name"],
            "commune": row["commune"],
            "membres": membres,
            "lignes": sorted(row["lignes"].split(","), key=lambda x: (len(x), x)),
            "texte_normalise": _normaliser(row["stop_name"]),
            "phonetique": code_phonetique(row["stop_name"]),
        })

    if fermer:
        conn.close()
    return arrets


def trouver_par_stop_id(stop_id, conn=None):
    """Retrouve l'arrêt logique (et donc tous ses quais) auquel appartient
    un stop_id donné."""
    for arret in charger_arrets_logiques(conn):
        if stop_id in arret["membres"]:
            return arret
    return None
