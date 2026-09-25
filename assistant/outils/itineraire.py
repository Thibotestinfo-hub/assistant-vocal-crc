"""
Outil `calculer_itineraire` — expérimental (voir docs/prochaines-etapes.md,
"punch-list déploiement" et section sur le calculateur d'itinéraire).
Contrat : docs/spec-assistant-vocal-v0-revisee.md, §4.

Périmètre volontairement limité, décidé avec l'utilisateur le 25/09/2026 :
- trajet direct sur une seule ligne, sinon une correspondance maximum ;
- théorique, comme horaires_theoriques (prévu, pas temps réel) ;
- au-delà d'une correspondance, on répond qu'on ne sait pas plutôt que
  d'inventer un trajet peu fiable (CLAUDE.md, exactitude).

Pas un vrai moteur de calcul d'itinéraire (RAPTOR ou équivalent) : une
recherche bornée aux prochains départs de l'arrêt de départ, pas une
exploration exhaustive de la journée — suffisant pour un réseau de cette
taille, pas généralisable à un réseau plus grand.
"""

from datetime import datetime, timedelta

from assistant.outils.arrets import charger_arrets_logiques
from assistant.outils.db import connexion_gtfs
from assistant.outils.horaires_theoriques import FUSEAU, _formater_heure, _services_actifs

# Délai de correspondance jugé réaliste : le temps de descendre et
# rejoindre le quai suivant (minimum), et une attente au-delà de
# laquelle mieux vaut ne rien proposer plutôt que décourager l'appelant
# (maximum).
CORRESPONDANCE_MIN_SECONDES = 3 * 60
CORRESPONDANCE_MAX_SECONDES = 45 * 60

# Nombre de départs à examiner depuis l'arrêt de départ pour chercher une
# correspondance — pas toute la journée, juste les prochains (voir
# docstring du module).
MAX_DEPARTS_EXAMINES = 6


def _prochains_departs_avec_trip(conn, membres, services, heure_secondes, limite):
    placeholders_membres = ",".join("?" * len(membres))
    placeholders_services = ",".join("?" * len(services))
    lignes = conn.execute(
        f"""
        SELECT st.trip_id, st.stop_sequence AS sequence_depart,
               st.departure_secondes AS depart_secondes,
               r.route_short_name, t.trip_headsign
        FROM stop_times st
        JOIN trips t ON t.trip_id = st.trip_id
        JOIN routes r ON r.route_id = t.route_id
        WHERE st.stop_id IN ({placeholders_membres})
          AND t.service_id IN ({placeholders_services})
          AND st.departure_secondes >= ?
        ORDER BY st.departure_secondes ASC
        """,
        (*membres, *services, heure_secondes),
    ).fetchall()
    return lignes[:limite]


def _trajet_direct(conn, arret_depart, arret_arrivee, services, heure_secondes):
    placeholders_dep = ",".join("?" * len(arret_depart["membres"]))
    placeholders_arr = ",".join("?" * len(arret_arrivee["membres"]))
    placeholders_services = ",".join("?" * len(services))
    ligne = conn.execute(
        f"""
        SELECT st1.departure_secondes AS depart_secondes, st2.arrival_secondes AS arrivee_secondes,
               r.route_short_name, t.trip_headsign
        FROM stop_times st1
        JOIN stop_times st2 ON st2.trip_id = st1.trip_id AND st2.stop_sequence > st1.stop_sequence
        JOIN trips t ON t.trip_id = st1.trip_id
        JOIN routes r ON r.route_id = t.route_id
        WHERE st1.stop_id IN ({placeholders_dep})
          AND st2.stop_id IN ({placeholders_arr})
          AND t.service_id IN ({placeholders_services})
          AND st1.departure_secondes >= ?
        ORDER BY st1.departure_secondes ASC
        LIMIT 1
        """,
        (*arret_depart["membres"], *arret_arrivee["membres"], *services, heure_secondes),
    ).fetchone()
    if not ligne:
        return None
    return {
        "type": "direct",
        "etapes": [{
            "ligne": ligne["route_short_name"],
            "destination": ligne["trip_headsign"],
            "depart": _formater_heure(ligne["depart_secondes"]),
            "arrivee": _formater_heure(ligne["arrivee_secondes"]),
        }],
    }


def _trajet_avec_correspondance(conn, arret_depart, arret_arrivee, services, heure_secondes, index_arrets):
    premiers_departs = _prochains_departs_avec_trip(
        conn, arret_depart["membres"], services, heure_secondes, MAX_DEPARTS_EXAMINES
    )
    lignes_arrivee = set(arret_arrivee["lignes"])
    meilleur = None

    for depart in premiers_departs:
        # Tous les arrêts desservis après le point de départ sur ce même trajet.
        descente = conn.execute(
            """
            SELECT st.stop_id, st.arrival_secondes
            FROM stop_times st
            WHERE st.trip_id = ? AND st.stop_sequence > ?
            ORDER BY st.stop_sequence ASC
            """,
            (depart["trip_id"], depart["sequence_depart"]),
        ).fetchall()

        for etape in descente:
            arret_transfert = index_arrets.get(etape["stop_id"])
            if arret_transfert is None or not lignes_arrivee & set(arret_transfert["lignes"]):
                continue

            heure_min_correspondance = etape["arrival_secondes"] + CORRESPONDANCE_MIN_SECONDES
            heure_max_correspondance = etape["arrival_secondes"] + CORRESPONDANCE_MAX_SECONDES
            second_trajet = _trajet_direct(
                conn, arret_transfert, arret_arrivee, services, heure_min_correspondance
            )
            if not second_trajet:
                continue
            depart_second = second_trajet["etapes"][0]
            depart_second_secondes = _secondes(depart_second["depart"])
            if depart_second_secondes > heure_max_correspondance:
                continue  # correspondance trop longue, on n'insiste pas

            arrivee_finale = _secondes(depart_second["arrivee"])
            if meilleur is None or arrivee_finale < meilleur["_arrivee_secondes"]:
                meilleur = {
                    "type": "correspondance",
                    "etapes": [
                        {
                            "ligne": depart["route_short_name"],
                            "destination": depart["trip_headsign"],
                            "depart": _formater_heure(depart["depart_secondes"]),
                            "arrivee": _formater_heure(etape["arrival_secondes"]),
                        },
                        {
                            "arret_correspondance": arret_transfert["stop_name"],
                            "commune_correspondance": arret_transfert["commune"],
                            **depart_second,
                        },
                    ],
                    "_arrivee_secondes": arrivee_finale,
                }

    if meilleur:
        del meilleur["_arrivee_secondes"]
    return meilleur


def _secondes(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 3600 + int(m) * 60


def calculer_itineraire(arret_depart_id, arret_arrivee_id, date=None, heure=None, conn=None):
    fermer = conn is None
    conn = conn or connexion_gtfs()

    # Un seul chargement de l'index des arrêts logiques pour toute la
    # fonction : charger_arrets_logiques() est une requête agrégée
    # coûteuse (~100-150 ms), et trouver_par_stop_id() la relançait à
    # chaque appel — deux fois rien que pour résoudre départ et arrivée,
    # avant même de savoir s'il y a une recherche à faire (budget de
    # 300 ms, voir CLAUDE.md).
    index_arrets = {
        stop_id: arret
        for arret in charger_arrets_logiques(conn)
        for stop_id in arret["membres"]
    }
    arret_depart = index_arrets.get(arret_depart_id)
    arret_arrivee = index_arrets.get(arret_arrivee_id)
    if arret_depart is None or arret_arrivee is None:
        if fermer:
            conn.close()
        return {"trouve": False, "erreur": "arret_depart_id ou arret_arrivee_id inconnu"}

    maintenant = datetime.now(FUSEAU)
    date_cible = datetime.strptime(date, "%Y-%m-%d").date() if date else maintenant.date()
    if heure:
        heure_secondes = _secondes(heure)
    elif date is None or date_cible == maintenant.date():
        heure_secondes = maintenant.hour * 3600 + maintenant.minute * 60 + maintenant.second
    else:
        heure_secondes = 0

    resultat = None
    for jours_decales in (0, 1):  # aujourd'hui, sinon demain (même logique que horaires_theoriques)
        jour = date_cible + timedelta(days=jours_decales)
        services = _services_actifs(conn, jour)
        if not services:
            continue
        base_secondes = heure_secondes if jours_decales == 0 else 0
        resultat = _trajet_direct(conn, arret_depart, arret_arrivee, services, base_secondes)
        if not resultat:
            resultat = _trajet_avec_correspondance(
                conn, arret_depart, arret_arrivee, services, base_secondes, index_arrets
            )
        if resultat:
            resultat["jour_decale"] = jours_decales
            break

    if fermer:
        conn.close()

    if not resultat:
        return {
            "trouve": False,
            "erreur": "aucun trajet direct ou avec une correspondance trouvé sur les prochains départs",
        }
    return {"trouve": True, **resultat}
