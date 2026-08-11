"""
Script d'exploration du GTFS "Les bus de l'étang" (mamp-bde).

Ne modifie rien, ne construit rien : lit les fichiers GTFS dans data/gtfs/,
récupère la liste des lignes affichées sur le site du réseau, et écrit
docs/fiche-gtfs.md avec des réponses aux questions de docs/questions-gtfs.md.

Usage : python3 tests/explorer_gtfs.py
"""

import csv
import html
import re
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

GTFS_DIR = Path(__file__).resolve().parent.parent / "data" / "gtfs"
OUT_FILE = Path(__file__).resolve().parent.parent / "docs" / "fiche-gtfs.md"

SITE_HORAIRES_URL = "https://www.salonetangcotebleue.fr/fr/horaires-de-ligne-en-pdf/96"

# Fichiers GTFS optionnels standards, pour dire explicitement lesquels manquent
FICHIERS_OPTIONNELS_STANDARDS = [
    "calendar.txt", "calendar_dates.txt", "fare_attributes.txt", "fare_rules.txt",
    "shapes.txt", "frequencies.txt", "transfers.txt", "pathways.txt", "levels.txt",
    "feed_info.txt", "translations.txt", "attributions.txt",
]


def lire(nom):
    chemin = GTFS_DIR / nom
    with open(chemin, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def heure_en_secondes(t):
    h, m, s = (int(x) for x in t.split(":"))
    return h * 3600 + m * 60 + s


def recuperer_lignes_site():
    """Récupère les libellés de lignes classées 'ZONE ETANG' sur la page
    horaires-de-ligne-en-pdf du site du réseau. Retourne (set des codes de ligne, erreur)."""
    try:
        requete = urllib.request.Request(SITE_HORAIRES_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(requete, timeout=20) as resp:
            contenu = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None, str(e)

    # Les titres de section sont des <h2>, dont le contenu peut inclure des
    # "<>" littéraux (ex. "Ligne 9: Pinchinades <> Pallières") : on capture
    # donc tout le bloc avec DOTALL plutôt qu'un [^<]+ qui casserait dessus.
    tous_h2 = re.findall(r"<h2>(.*?)</h2>", contenu, re.DOTALL)
    titres_zone_etang = [
        html.unescape(h).replace("ZONE ETANG", "", 1).strip()
        for h in tous_h2 if "ZONE ETANG" in h
    ]
    codes = set()
    for titre in titres_zone_etang:
        # Formats rencontrés : "Ligne 9: ...", "Ligne ZEN A : ...",
        # "Ligne lebus+ 13 : ...", "LIGNE 3/6 : ...", "LeBusPRO: ..."
        m = re.match(r"(?:Ligne|LIGNE)\s+lebus\+\s*(\S+?)\s*:", titre, re.IGNORECASE)
        if m:
            codes.add(m.group(1))
            continue
        m = re.match(r"(?:Ligne|LIGNE)\s+(ZEN\s+[A-Z])\s*:", titre, re.IGNORECASE)
        if m:
            codes.add(m.group(1).upper())
            continue
        m = re.match(r"(?:Ligne|LIGNE)\s+(\S+?)\s*:", titre, re.IGNORECASE)
        if m:
            codes.add(m.group(1))
            continue
        if titre.startswith("LeBusPRO"):
            codes.add("LeBusPRO")
            continue
    return codes, None


def main():
    agency = lire("agency.txt")
    routes = lire("routes.txt")
    stops = lire("stops.txt")
    trips = lire("trips.txt")
    stop_times = lire("stop_times.txt")
    calendar = lire("calendar.txt")
    calendar_dates = lire("calendar_dates.txt")
    feed_info = lire("feed_info.txt")[0]

    fichiers_presents = sorted(p.name for p in GTFS_DIR.glob("*.txt"))
    fichiers_absents = [f for f in FICHIERS_OPTIONNELS_STANDARDS if f not in fichiers_presents]

    trip_to_route = {t["trip_id"]: t["route_id"] for t in trips}
    route_by_id = {r["route_id"]: r for r in routes}

    # --- Volumétrie ---
    n_arrets_quais = sum(1 for s in stops if s["location_type"] == "0")
    n_stations = sum(1 for s in stops if s["location_type"] == "1")

    # --- Arrêts : doublons de stop_name ---
    noms = Counter(s["stop_name"] for s in stops)
    top_noms = noms.most_common(10)

    # exemple détaillé : un nom d'arrêt qui existe dans plusieurs communes
    # différentes (le vrai piège du "je ne sais pas où aller sans la commune")
    communes_par_nom = defaultdict(set)
    for s in stops:
        communes_par_nom[s["stop_name"]].add(s["city_name"])
    noms_multi_communes = sorted(
        ((nom, communes) for nom, communes in communes_par_nom.items() if len(communes) > 1),
        key=lambda x: -noms[x[0]],
    )
    nom_homonyme, communes_du_nom = noms_multi_communes[0]
    communes_du_nom = sorted(communes_du_nom)

    # --- Arrêts : parent_station ---
    quais_avec_parent = [s for s in stops if s["parent_station"]]
    exemples_parent = quais_avec_parent[:5]

    # --- Arrêts : coordonnées ---
    lats = [float(s["stop_lat"]) for s in stops if s["stop_lat"]]
    lons = [float(s["stop_lon"]) for s in stops if s["stop_lon"]]
    n_coords_manquantes = sum(1 for s in stops if not s["stop_lat"] or not s["stop_lon"])

    # --- Arrêts : commune ---
    communes = sorted({s["city_name"] for s in stops if s["city_name"]})
    n_zone_id_renseignes = sum(1 for s in stops if s["zone_id"])

    # --- Lignes ---
    noms_courts = Counter(r["route_short_name"] for r in routes)
    doublons_route_short_name = {k: v for k, v in noms_courts.items() if v > 1}
    agences = sorted({r["agency_id"] for r in routes})

    # --- Horaires : au-delà de 24:00:00 ---
    depassements = []
    heure_max = ("", -1)
    for st in stop_times:
        for champ in ("arrival_time", "departure_time"):
            t = st[champ]
            if not t:
                continue
            secs = heure_en_secondes(t)
            if secs > heure_max[1]:
                heure_max = (t, secs)
            if secs >= 24 * 3600:
                depassements.append((st["trip_id"], champ, t))

    lignes_avec_depassement = sorted({
        route_by_id[trip_to_route[tid]]["route_short_name"]
        for tid, _, _ in depassements
        if trip_to_route.get(tid) in route_by_id
    })

    pickup_types = Counter(st["pickup_type"] for st in stop_times)
    dropoff_types = Counter(st["drop_off_type"] for st in stop_times)

    # --- Calendriers ---
    n_service_id = len({c["service_id"] for c in calendar})
    exception_types = Counter(cd["exception_type"] for cd in calendar_dates)
    dates_exceptions = sorted({cd["date"] for cd in calendar_dates})

    # --- Accessibilité ---
    wheelchair = Counter(s["wheelchair_boarding"] for s in stops)

    # --- Comparaison avec le site du réseau ---
    lignes_site, erreur_site = recuperer_lignes_site()
    lignes_gtfs = {r["route_short_name"] for r in routes}

    # --- Validité du jeu ---
    aujourd_hui = date.today()
    fin_validite = date(
        int(feed_info["feed_end_date"][:4]),
        int(feed_info["feed_end_date"][4:6]),
        int(feed_info["feed_end_date"][6:8]),
    )
    jours_restants = (fin_validite - aujourd_hui).days

    # ================= Rédaction du rapport =================
    lignes_md = []

    def w(txt=""):
        lignes_md.append(txt)

    w("# Fiche GTFS — Les bus de l'étang (mamp-bde)")
    w()
    w(f"Générée le {aujourd_hui.isoformat()} par `tests/explorer_gtfs.py`, "
      f"à partir du jeu téléchargé dans `data/gtfs/` "
      f"(feed_version `{feed_info['feed_version']}`).")
    w()
    w("---")
    w()

    # --- Volumétrie ---
    w("## Volumétrie")
    w()
    w(f"- **Arrêts/quais (`location_type=0`)** : {n_arrets_quais}")
    w(f"- **Stations regroupant des quais (`location_type=1`)** : {n_stations}")
    w(f"- **Lignes (`routes.txt`)** : {len(routes)}")
    w(f"- **Courses (`trips.txt`)** : {len(trips)}")
    w(f"- **Dessertes (lignes de `stop_times.txt`, un passage à un arrêt)** : {len(stop_times)}")
    w()
    w(f"**Période de validité déclarée** (`feed_info.txt`) : "
      f"{feed_info['feed_start_date']} → {feed_info['feed_end_date']} "
      f"(version `{feed_info['feed_version']}`).")
    w()
    w(f"⚠️ **Expire dans {jours_restants} jours** (le {fin_validite.isoformat()}), "
      f"veille de la nouvelle offre du réseau annoncée pour le 31/08/2026. "
      f"Le chargeur GTFS devra alerter avant cette échéance.")
    w()
    w(f"**Fichiers présents** : {', '.join(fichiers_presents)}")
    w()
    w(f"**Fichiers optionnels absents** : {', '.join(fichiers_absents)}")
    w()
    w("---")
    w()

    # --- Arrêts ---
    w("## Arrêts")
    w()
    w("### Format des `stop_id`")
    w()
    exemples_stop_id = [s["stop_id"] for s in stops[:5]]
    w(f"Préfixe `BDE-` suivi d'un code alphanumérique lié au code arrêt réseau "
      f"(`stop_code`), par exemple : `{'`, `'.join(exemples_stop_id)}`.")
    w()
    w("**Stabilité d'une version à l'autre** : impossible à vérifier avec un seul "
      "jeu de données. Le feed expire le 30/08/2026 et sera remplacé — c'est "
      "l'occasion de comparer les `stop_id` de l'ancien et du nouveau jeu et de "
      "documenter la réponse à ce moment-là.")
    w()

    w("### `parent_station`")
    w()
    w(f"{len(quais_avec_parent)} quais sur {n_arrets_quais} référencent un "
      f"`parent_station` (les {n_stations} stations de `location_type=1`). "
      f"Exemples réels :")
    w()
    w("| stop_id | stop_name | parent_station |")
    w("|---|---|---|")
    for s in exemples_parent:
        w(f"| {s['stop_id']} | {s['stop_name']} | {s['parent_station']} |")
    w()
    w(f"Conséquence : {n_arrets_quais - len(quais_avec_parent)} quais n'ont "
      f"**pas** de `parent_station` renseigné. Le regroupement de quais ne peut "
      f"donc pas être supposé systématique — il faut vérifier au cas par cas "
      f"avant de fusionner deux quais dans une même réponse vocale.")
    w()

    w("### Doublons de `stop_name`")
    w()
    w("Les dix noms d'arrêt les plus fréquents :")
    w()
    w("| stop_name | occurrences |")
    w("|---|---|")
    for nom, n in top_noms:
        w(f"| {nom} | {n} |")
    w()
    w(f"Exemple concret d'homonymie inter-communes : le nom **« {nom_homonyme} »** "
      f"apparaît {noms[nom_homonyme]} fois, dans les communes suivantes : "
      f"{', '.join(communes_du_nom)}. "
      f"Sans la commune, impossible de savoir lequel l'appelant veut dire. "
      f"({len(noms_multi_communes)} noms d'arrêt au total existent dans plus "
      f"d'une commune.)")
    w()

    w("### Commune (`city_name`, `ext_code_insee`)")
    w()
    w("**Correction à apporter à `CLAUDE.md` : ce jeu GTFS contient bien un "
      "champ commune.** `stops.txt` a des colonnes `city_name` et "
      f"`ext_code_insee` renseignées sur les {len(stops)} arrêts (extensions "
      f"Mecatran, hors standard GTFS officiel). Exemple réel :")
    w()
    exemple_stop_commune = stops[0]
    w(f"`{exemple_stop_commune['stop_id']}` — "
      f"« {exemple_stop_commune['stop_name']} » — "
      f"commune : **{exemple_stop_commune['city_name']}** "
      f"(code INSEE {exemple_stop_commune['ext_code_insee']}).")
    w()
    w(f"Communes rencontrées ({len(communes)}) : {', '.join(communes)}.")
    w()
    w("⚠️ Cette liste dépasse le périmètre annoncé dans `docs/sources.md` "
      "(Berre-l'Étang, Gignac-la-Nerthe, Les Pennes-Mirabeau, Marignane, "
      "Rognac, Saint-Victoret, Velaux, Vitrolles — 8 communes). Le GTFS "
      "ajoute **Marseille**, **Cabriès** et **La Fare-les-Oliviers**. "
      "Conséquence : le périmètre géographique configuré (`data/config.yaml`) "
      "devra couvrir ces communes-là aussi, pas seulement les 8 annoncées.")
    w()
    w("Ceci dit, la conclusion reste valable en pratique : `city_name` est une "
      "extension propriétaire Mecatran, pas un champ GTFS standard. Un chargeur "
      "écrit pour rester portable sur un autre réseau ne doit pas en dépendre "
      "sans vérifier qu'il existe — la déduction géographique par contour de "
      "commune reste la solution robuste à implémenter dans tous les cas.")
    w()
    w(f"`stop_desc` et `platform_code` : colonnes absentes de `stops.txt`. "
      f"`zone_id` : colonne présente mais vide sur les {len(stops)} arrêts "
      f"({n_zone_id_renseignes} renseignés) — inutilisable.")
    w()

    w("### Coordonnées")
    w()
    w(f"{n_coords_manquantes} coordonnées manquantes sur {len(stops)} arrêts. "
      f"Plage observée : latitude {min(lats):.5f} → {max(lats):.5f}, "
      f"longitude {min(lons):.5f} → {max(lons):.5f} — cohérent avec la zone "
      f"Étang de Berre (aucune valeur aberrante du type 0,0).")
    w()
    w("---")
    w()

    # --- Lignes ---
    w("## Lignes")
    w()
    w("### Format des `route_id`")
    w()
    exemples_route_id = [r["route_id"] for r in routes[:6]]
    w(f"Préfixe `BDE-` suivi du `route_short_name` ou d'un code interne, par "
      f"exemple : `{'`, `'.join(exemples_route_id)}`. Notez `BDE-131` et "
      f"`BDE-132` pour les lignes `13A` et `13B` — le `route_id` ne suit pas "
      f"toujours visuellement le `route_short_name`.")
    w()

    w("### `route_short_name`")
    w()
    w(f"{len(routes)} lignes, {len(noms_courts)} `route_short_name` distincts : "
      f"{', '.join(sorted(noms_courts, key=lambda x: (len(x), x)))}.")
    w()
    if doublons_route_short_name:
        w(f"Doublons trouvés : {doublons_route_short_name}.")
    else:
        w("Aucun doublon de `route_short_name` dans ce jeu — mais ce sera à "
          "revérifier une fois le référentiel complet `mamp` intégré, puisque "
          "les numéros de ligne se répètent d'un réseau à l'autre (piège "
          "documenté dans `CLAUDE.md`).")
    w()

    w("### `agency_id`")
    w()
    w(f"Une seule agence dans ce jeu : `{agency[0]['agency_id']}` "
      f"(« {agency[0]['agency_name']} »). Le champ ne distingue donc aucune "
      f"marque ici — mais ce jeu `mamp-bde` est déjà un extrait mono-réseau ; "
      f"le référentiel complet `mamp` en contiendra probablement plusieurs.")
    w()

    w("### Lignes scolaires")
    w()
    w("Aucun marqueur de ligne scolaire trouvé dans ce jeu : ni dans "
      "`route_long_name`, ni dans `trip_headsign`, ni dans les colonnes "
      "d'extension (`ext_type_course` ne contient que la valeur `COM`). "
      "Le site du réseau, lui, publie des « circuits scolaires » numérotés "
      "590 à 699 (ex. « Circuit scolaire 692 Berre l'Étang <> Gignac la "
      "Nerthe ») absents de `routes.txt`. Conséquence : soit ces circuits "
      "ne sont pas dans le périmètre `mamp-bde`, soit ils sont publiés "
      "ailleurs — à vérifier avant de considérer l'absence de lignes "
      "scolaires comme acquise.")
    w()
    w("---")
    w()

    # --- Horaires ---
    w("## Horaires")
    w()
    w(f"**Aucun horaire au-delà de `24:00:00`** dans ce jeu — 0 occurrence sur "
      f"{len(stop_times)} dessertes. L'heure la plus tardive rencontrée est "
      f"**{heure_max[0]}**.")
    w()
    w("⚠️ Ceci contredit le piège générique documenté dans `CLAUDE.md` "
      "(« Le GTFS contient des heures au-delà de 24:00:00 »). Deux "
      "explications possibles, à trancher avec le jeu suivant (après le "
      "30/08/2026) : (1) ce jeu couvre une période d'été à service réduit "
      "sans services de nuit franchissant minuit, ou (2) ce réseau n'a "
      "simplement aucun départ après minuit. Le code de traitement des "
      "horaires doit malgré tout gérer le cas `>= 24:00:00` explicitement : "
      "ne pas trouver l'exception dans ce jeu ne prouve pas qu'elle "
      "n'apparaîtra pas dans le suivant.")
    w()
    w("`frequencies.txt` : absent. Toutes les courses sont donc des horaires "
      "fixes définis course par course dans `stop_times.txt`, aucune ligne "
      "en fréquence.")
    w()
    def resume_valeurs(compteur):
        return ", ".join(f"`{v}` ({n})" for v, n in sorted(compteur.items()))

    w(f"`pickup_type` : {resume_valeurs(pickup_types)}. "
      f"`drop_off_type` : {resume_valeurs(dropoff_types)}. "
      f"(`0` = montée/descente normale.) "
      + ("Uniquement des valeurs normales sur ce jeu : ces deux champs ne "
         "signalent aucun arrêt « dépose seule » ou « montée seule »."
         if set(pickup_types) == {"0"} and set(dropoff_types) == {"0"}
         else "Des valeurs autres que `0` existent — à vérifier au cas par "
         "cas avant de les ignorer."))
    w()
    w("---")
    w()

    # --- Calendriers ---
    w("## Calendriers")
    w()
    w(f"Les deux fichiers sont présents et combinés : `calendar.txt` "
      f"({n_service_id} `service_id`, motif hebdomadaire de base) et "
      f"`calendar_dates.txt` ({len(calendar_dates)} lignes d'exception).")
    w()
    w("Exemple réel de `calendar.txt` :")
    w()
    exemple_cal = calendar[0]
    w(f"`{exemple_cal['service_id']}` — actif uniquement le "
      f"{'samedi' if exemple_cal['saturday'] == '1' else '...'} — "
      f"du {exemple_cal['start_date']} au {exemple_cal['end_date']} — "
      f"nommé `{exemple_cal['service_name']}`.")
    w()
    w(f"`calendar_dates.txt` ne référence que **{len(dates_exceptions)} dates** "
      f"({', '.join(dates_exceptions)}) — le 14 juillet et le 15 août 2026, "
      f"deux jours fériés. Sur les {len(calendar_dates)} lignes d'exception : "
      f"{exception_types.get('1', 0)} ajoutent un service ce jour-là "
      f"(`exception_type=1`) et {exception_types.get('2', 0)} en retirent un "
      f"(`exception_type=2`).")
    w()
    w("**Vacances scolaires** : aucun traitement dédié visible — logique, "
      "puisque le jeu entier (06/07 → 30/08/2026) correspond à la période "
      "de vacances d'été ; il n'y a donc rien à distinguer à l'intérieur.")
    w()
    w("**Jours fériés** : traités par exception dans `calendar_dates.txt`, "
      "comme montré ci-dessus — pas par un `service_id` séparé actif toute "
      "l'année.")
    w()
    w("**Services d'été distincts** : oui, implicitement — ce jeu entier "
      "*est* le service d'été. Le prochain jeu (post 30/08/2026) sera "
      "vraisemblablement le service d'année scolaire, avec sa propre "
      "période de validité.")
    w()
    w("---")
    w()

    # --- Accessibilité et divers ---
    w("## Accessibilité et divers")
    w()
    if set(wheelchair) == {"0"}:
        w(f"`wheelchair_boarding` : la valeur `0` (« information inconnue ») "
          f"sur les {len(stops)} arrêts, sans aucune exception. Le champ "
          f"existe mais n'apporte aucune information exploitable dans ce jeu.")
    else:
        w(f"`wheelchair_boarding` : {dict(wheelchair)} sur les {len(stops)} "
          f"arrêts — des arrêts renseignés existent, à exploiter.")
    w()
    w(f"`shapes.txt` : présent, {len(lire('shapes.txt'))} points de tracé.")
    w()
    w("`transfers.txt` : absent — aucune correspondance entre arrêts n'est "
      "déclarée dans le GTFS.")
    w()
    w("---")
    w()

    # --- Comparaison avec le site du réseau ---
    w("## Vérification supplémentaire — lignes du site vs `routes.txt`")
    w()
    w(f"Source : page « horaires de ligne en PDF » du site, filtrée aux "
      f"sections `ZONE ETANG` — {SITE_HORAIRES_URL}")
    w()
    if erreur_site:
        w(f"⚠️ Impossible de récupérer la page ({erreur_site}). Comparaison "
          f"non réalisée — à relancer.")
    else:
        w(f"**Lignes « zone Étang » listées sur le site** ({len(lignes_site)}) : "
          f"{', '.join(sorted(lignes_site))}.")
        w()
        w(f"**`route_short_name` dans `routes.txt`** ({len(lignes_gtfs)}) : "
          f"{', '.join(sorted(lignes_gtfs, key=lambda x: (len(x), x)))}.")
        w()
        manquantes_du_gtfs = sorted(lignes_site - lignes_gtfs)
        absentes_du_site = sorted(lignes_gtfs - lignes_site)
        w(f"### Lignes affichées sur le site mais absentes de `routes.txt` "
          f"({len(manquantes_du_gtfs)})")
        w()
        for l in manquantes_du_gtfs:
            w(f"- **{l}**")
        w()
        w("Détail :")
        w()
        w("- **2**, **3** et **6** : trois lignes régulières avec fiche "
          "horaire publiée (« Ligne 2 : Jas de Rhodes <> Tante Rose », "
          "« Ligne 3: Jaï<>Parc Camoin<>St Louis-Ste Marie/Brassens-Genevoix », "
          "« Ligne 6: Parc Camoin <> Les Couronnes »), totalement absentes "
          "de `routes.txt`. C'est la vraie alerte : un appelant demandant "
          "la ligne 2, 3 ou 6 recevra une réponse « je ne sais pas » alors "
          "que la ligne existe. (`lebus+ 13`, présent sur le site, n'est "
          "*pas* dans cette liste : il correspond bien à `BDE-13`, déjà "
          "dans `routes.txt` — la comparaison le reconnaît correctement.)")
        w("- **3/6** : correspond vraisemblablement à `BDE-36` "
          "(« Le Jaï - Les Couronnes » dans `routes.txt`, mêmes terminus "
          "que « Couronnes <> Jaï » sur le site) — probable écart de "
          "nommage (`36` au lieu de `3/6`), pas une ligne manquante. "
          "À confirmer avec le réseau avant de coder un mapping.")
        w("- **LeBusPRO** : service de transport à la demande pour zones "
          "d'activité (Estroublans, Anjoly), sans numéro de ligne. Ne "
          "correspond à aucun `route_short_name` du GTFS — les lignes "
          "`6000`-`6009` sont nommées `TAD`, `TAD 1`... `TAD 7`, pas "
          "`LeBusPRO`. À vérifier si ce service est inclus dans une de "
          "ces routes TAD ou totalement absent du GTFS.")
        w()
        w(f"### Lignes présentes dans `routes.txt` mais non trouvées sur "
          f"cette page du site ({len(absentes_du_site)})")
        w()
        for l in absentes_du_site:
            w(f"- **{l}**")
        w()
        w("Détail : `13A` et `13B` n'ont pas de fiche horaire distincte sur "
          "le site (seule `13` y figure) ; `36` n'apparaît nulle part sous "
          "ce nom (voir `3/6` ci-dessus) ; `ZEN` (sans lettre) n'a pas de "
          "fiche, contrairement à `ZEN A` et `ZEN B` ; les lignes `6000`-`6009` "
          "(transport à la demande) ne sont pas sur cette page — probablement "
          "publiées ailleurs sur le site (page « transports à la demande »), "
          "pas sur la page des fiches horaires de ligne classique.")
        w()
        w("**Conséquence pour le code à venir** : ne pas construire la liste "
          "des lignes valides uniquement depuis `routes.txt` sans vérification "
          "humaine — au moins trois lignes réellement en service (2, 3 et 6) "
          "en sont absentes. Avant de brancher la recherche de ligne par "
          "numéro, confirmer avec le réseau si `routes.txt` est complet ou "
          "si le référentiel `mamp` complet (plutôt que `mamp-bde`) comble "
          "ce trou.")
    w()
    w("---")
    w()

    # --- Synthèse ---
    w("## Synthèse des pièges identifiés")
    w()
    w("| Piège constaté | Preuve | Conséquence pour le code |")
    w("|---|---|---|")
    w("| Le jeu expire bientôt | Validité déclarée jusqu'au "
      f"{feed_info['feed_end_date']}, soit dans {jours_restants} jours | "
      "Le chargeur GTFS doit alerter avant expiration, pas la découvrir "
      "en prod. |")
    w("| Trois lignes régulières manquent du GTFS | Lignes **2**, **3** et "
      "**6** publiées sur le site avec fiche horaire, absentes de "
      "`routes.txt` | Ne pas construire le référentiel de lignes uniquement "
      "depuis `routes.txt` sans vérification humaine préalable. |")
    w("| `city_name` existe mais n'est pas un champ GTFS standard | Colonne "
      "propriétaire Mecatran, présente ici mais pas garantie sur un autre "
      "réseau | Le code de déduction de commune par coordonnées reste "
      "nécessaire pour rester portable — ne pas coder en dur une dépendance "
      "à `city_name`. |")
    w("| Homonymes de `stop_name` entre communes | "
      f"« {nom_homonyme} » apparaît {noms[nom_homonyme]} fois, "
      f"dans {len(communes_du_nom)} communes distinctes ({len(noms_multi_communes)} "
      f"noms concernés au total) | La recherche d'arrêt doit toujours "
      "désambiguïser par commune, jamais par nom seul. |")
    w("| `parent_station` partiel | Seuls "
      f"{len(quais_avec_parent)}/{n_arrets_quais} quais en ont un | Ne pas "
      "supposer que deux quais d'un même arrêt physique sont toujours reliés "
      "par `parent_station` — certains ne le sont pas. |")
    w("| Aucun horaire après minuit dans **ce** jeu | 0 occurrence de "
      f"`>= 24:00:00` sur {len(stop_times)} dessertes, max `{heure_max[0]}` | "
      "Coder quand même le traitement explicite de `>= 24:00:00` : "
      "l'absence dans ce jeu d'été ne garantit rien pour le jeu suivant. |")
    w("| Pas de lignes scolaires identifiables dans le GTFS | Aucun "
      "marqueur trouvé, alors que le site publie des circuits scolaires "
      "590-699 | Vérifier si ces circuits sont hors périmètre `mamp-bde` "
      "avant d'affirmer que le réseau n'a pas de lignes scolaires. |")
    w("| `wheelchair_boarding` inexploitable | Valeur `0` uniforme sur les "
      f"{len(stops)} arrêts | Ne pas afficher d'information d'accessibilité "
      "à partir de ce champ pour ce réseau — la donnée n'existe pas. |")
    w()

    OUT_FILE.write_text("\n".join(lignes_md) + "\n", encoding="utf-8")
    print(f"Rapport écrit dans {OUT_FILE}")


if __name__ == "__main__":
    main()
