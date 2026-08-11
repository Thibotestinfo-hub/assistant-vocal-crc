# Fiche GTFS — Les bus de l'étang (mamp-bde)

Générée le 2026-08-10 par `tests/explorer_gtfs.py`, à partir du jeu téléchargé dans `data/gtfs/` (feed_version `06/07/2026-12:34`).

---

## Volumétrie

- **Arrêts/quais (`location_type=0`)** : 666
- **Stations regroupant des quais (`location_type=1`)** : 173
- **Lignes (`routes.txt`)** : 26
- **Courses (`trips.txt`)** : 1388
- **Dessertes (lignes de `stop_times.txt`, un passage à un arrêt)** : 29728

**Période de validité déclarée** (`feed_info.txt`) : 20260706 → 20260830 (version `06/07/2026-12:34`).

⚠️ **Expire dans 20 jours** (le 2026-08-30), veille de la nouvelle offre du réseau annoncée pour le 31/08/2026. Le chargeur GTFS devra alerter avant cette échéance.

**Fichiers présents** : agency.txt, calendar.txt, calendar_dates.txt, feed_info.txt, routes.txt, shapes.txt, stop_times.txt, stops.txt, trips.txt

**Fichiers optionnels absents** : fare_attributes.txt, fare_rules.txt, frequencies.txt, transfers.txt, pathways.txt, levels.txt, translations.txt, attributions.txt

---

## Arrêts

### Format des `stop_id`

Préfixe `BDE-` suivi d'un code alphanumérique lié au code arrêt réseau (`stop_code`), par exemple : `BDE-AMU1`, `BDE-AMU2`, `BDE-AHE1`, `BDE-ARO1`, `BDE-ARO2`.

**Stabilité d'une version à l'autre** : impossible à vérifier avec un seul jeu de données. Le feed expire le 30/08/2026 et sera remplacé — c'est l'occasion de comparer les `stop_id` de l'ancien et du nouveau jeu et de documenter la réponse à ce moment-là.

### `parent_station`

206 quais sur 666 référencent un `parent_station` (les 173 stations de `location_type=1`). Exemples réels :

| stop_id | stop_name | parent_station |
|---|---|---|
| BDE-21847 | Abbadie musée | BDE-AMU1 |
| BDE-23110 | Abbadie Musée | BDE-AMU2 |
| BDE-20699 | Acacias | BDE-LAC1 |
| BDE-25187 | Acacias | BDE-LAC2 |
| BDE-23497 | AIRBUS Hélicopte | BDE-AHE1 |

Conséquence : 460 quais n'ont **pas** de `parent_station` renseigné. Le regroupement de quais ne peut donc pas être supposé systématique — il faut vérifier au cas par cas avant de fusionner deux quais dans une même réponse vocale.

### Doublons de `stop_name`

Les dix noms d'arrêt les plus fréquents :

| stop_name | occurrences |
|---|---|
| Pierre Plantée - | 16 |
| Clinique | 6 |
| Les Couronnes | 6 |
| Carbonel | 5 |
| Square de Gaulle | 5 |
| Victor Hugo | 5 |
| Athènes Rome | 4 |
| Base Nautique | 4 |
| Berlioz | 4 |
| Cabrianne Ouest | 4 |

Exemple concret d'homonymie inter-communes : le nom **« Clinique »** apparaît 6 fois, dans les communes suivantes : Marignane, Rognac. Sans la commune, impossible de savoir lequel l'appelant veut dire. (10 noms d'arrêt au total existent dans plus d'une commune.)

### Commune (`city_name`, `ext_code_insee`)

**Correction à apporter à `CLAUDE.md` : ce jeu GTFS contient bien un champ commune.** `stops.txt` a des colonnes `city_name` et `ext_code_insee` renseignées sur les 839 arrêts (extensions Mecatran, hors standard GTFS officiel). Exemple réel :

`BDE-AMU1` — « Abbadie musée » — commune : **Saint-Victoret** (code INSEE 13102).

Communes rencontrées (11) : Berre-l'Étang, Cabriès, Gignac-la-Nerthe, La Fare-les-Oliviers, Les Pennes-Mirabeau, Marignane, Marseille, Rognac, Saint-Victoret, Velaux, Vitrolles.

⚠️ Cette liste dépasse le périmètre annoncé dans `docs/sources.md` (Berre-l'Étang, Gignac-la-Nerthe, Les Pennes-Mirabeau, Marignane, Rognac, Saint-Victoret, Velaux, Vitrolles — 8 communes). Le GTFS ajoute **Marseille**, **Cabriès** et **La Fare-les-Oliviers**. Conséquence : le périmètre géographique configuré (`data/config.yaml`) devra couvrir ces communes-là aussi, pas seulement les 8 annoncées.

Ceci dit, la conclusion reste valable en pratique : `city_name` est une extension propriétaire Mecatran, pas un champ GTFS standard. Un chargeur écrit pour rester portable sur un autre réseau ne doit pas en dépendre sans vérifier qu'il existe — la déduction géographique par contour de commune reste la solution robuste à implémenter dans tous les cas.

`stop_desc` et `platform_code` : colonnes absentes de `stops.txt`. `zone_id` : colonne présente mais vide sur les 839 arrêts (0 renseignés) — inutilisable.

### Coordonnées

0 coordonnées manquantes sur 839 arrêts. Plage observée : latitude 43.36961 → 43.55041, longitude 5.11676 → 5.37454 — cohérent avec la zone Étang de Berre (aucune valeur aberrante du type 0,0).

---

## Lignes

### Format des `route_id`

Préfixe `BDE-` suivi du `route_short_name` ou d'un code interne, par exemple : `BDE-1`, `BDE-5`, `BDE-7`, `BDE-8`, `BDE-9`, `BDE-10`. Notez `BDE-131` et `BDE-132` pour les lignes `13A` et `13B` — le `route_id` ne suit pas toujours visuellement le `route_short_name`.

### `route_short_name`

26 lignes, 26 `route_short_name` distincts : 1, 5, 7, 8, 9, 10, 11, 12, 13, 14, 18, 20, 36, 13A, 13B, ZEN, 6000, 6001, 6002, 6003, 6004, 6005, 6008, 6009, ZEN A, ZEN B.

Aucun doublon de `route_short_name` dans ce jeu — mais ce sera à revérifier une fois le référentiel complet `mamp` intégré, puisque les numéros de ligne se répètent d'un réseau à l'autre (piège documenté dans `CLAUDE.md`).

### `agency_id`

Une seule agence dans ce jeu : `BDE` (« Est Étang »). Le champ ne distingue donc aucune marque ici — mais ce jeu `mamp-bde` est déjà un extrait mono-réseau ; le référentiel complet `mamp` en contiendra probablement plusieurs.

### Lignes scolaires

Aucun marqueur de ligne scolaire trouvé dans ce jeu : ni dans `route_long_name`, ni dans `trip_headsign`, ni dans les colonnes d'extension (`ext_type_course` ne contient que la valeur `COM`). Le site du réseau, lui, publie des « circuits scolaires » numérotés 590 à 699 (ex. « Circuit scolaire 692 Berre l'Étang <> Gignac la Nerthe ») absents de `routes.txt`. Conséquence : soit ces circuits ne sont pas dans le périmètre `mamp-bde`, soit ils sont publiés ailleurs — à vérifier avant de considérer l'absence de lignes scolaires comme acquise.

---

## Horaires

**Aucun horaire au-delà de `24:00:00`** dans ce jeu — 0 occurrence sur 29728 dessertes. L'heure la plus tardive rencontrée est **22:59:00**.

⚠️ Ceci contredit le piège générique documenté dans `CLAUDE.md` (« Le GTFS contient des heures au-delà de 24:00:00 »). Deux explications possibles, à trancher avec le jeu suivant (après le 30/08/2026) : (1) ce jeu couvre une période d'été à service réduit sans services de nuit franchissant minuit, ou (2) ce réseau n'a simplement aucun départ après minuit. Le code de traitement des horaires doit malgré tout gérer le cas `>= 24:00:00` explicitement : ne pas trouver l'exception dans ce jeu ne prouve pas qu'elle n'apparaîtra pas dans le suivant.

`frequencies.txt` : absent. Toutes les courses sont donc des horaires fixes définis course par course dans `stop_times.txt`, aucune ligne en fréquence.

`pickup_type` : `0` (29728). `drop_off_type` : `0` (29728). (`0` = montée/descente normale.) Uniquement des valeurs normales sur ce jeu : ces deux champs ne signalent aucun arrêt « dépose seule » ou « montée seule ».

---

## Calendriers

Les deux fichiers sont présents et combinés : `calendar.txt` (12 `service_id`, motif hebdomadaire de base) et `calendar_dates.txt` (12 lignes d'exception).

Exemple réel de `calendar.txt` :

`BDE-08537b0135` — actif uniquement le samedi — du 20260711 au 20260829 — nommé `HAB SI 11 PAS VALIDEE [Sat]`.

`calendar_dates.txt` ne référence que **2 dates** (20260714, 20260815) — le 14 juillet et le 15 août 2026, deux jours fériés. Sur les 12 lignes d'exception : 5 ajoutent un service ce jour-là (`exception_type=1`) et 7 en retirent un (`exception_type=2`).

**Vacances scolaires** : aucun traitement dédié visible — logique, puisque le jeu entier (06/07 → 30/08/2026) correspond à la période de vacances d'été ; il n'y a donc rien à distinguer à l'intérieur.

**Jours fériés** : traités par exception dans `calendar_dates.txt`, comme montré ci-dessus — pas par un `service_id` séparé actif toute l'année.

**Services d'été distincts** : oui, implicitement — ce jeu entier *est* le service d'été. Le prochain jeu (post 30/08/2026) sera vraisemblablement le service d'année scolaire, avec sa propre période de validité.

---

## Accessibilité et divers

`wheelchair_boarding` : la valeur `0` (« information inconnue ») sur les 839 arrêts, sans aucune exception. Le champ existe mais n'apporte aucune information exploitable dans ce jeu.

`shapes.txt` : présent, 52834 points de tracé.

`transfers.txt` : absent — aucune correspondance entre arrêts n'est déclarée dans le GTFS.

---

## Vérification supplémentaire — lignes du site vs `routes.txt`

Source : page « horaires de ligne en PDF » du site, filtrée aux sections `ZONE ETANG` — https://www.salonetangcotebleue.fr/fr/horaires-de-ligne-en-pdf/96

**Lignes « zone Étang » listées sur le site** (19) : 1, 10, 11, 12, 13, 14, 18, 2, 20, 3, 3/6, 5, 6, 7, 8, 9, LeBusPRO, ZEN A, ZEN B.

**`route_short_name` dans `routes.txt`** (26) : 1, 5, 7, 8, 9, 10, 11, 12, 13, 14, 18, 20, 36, 13A, 13B, ZEN, 6000, 6001, 6002, 6003, 6004, 6005, 6008, 6009, ZEN A, ZEN B.

### Lignes affichées sur le site mais absentes de `routes.txt` (5)

- **2**
- **3**
- **3/6**
- **6**
- **LeBusPRO**

Détail :

- **2**, **3** et **6** : trois lignes régulières avec fiche horaire publiée (« Ligne 2 : Jas de Rhodes <> Tante Rose », « Ligne 3: Jaï<>Parc Camoin<>St Louis-Ste Marie/Brassens-Genevoix », « Ligne 6: Parc Camoin <> Les Couronnes »), totalement absentes de `routes.txt`. C'est la vraie alerte : un appelant demandant la ligne 2, 3 ou 6 recevra une réponse « je ne sais pas » alors que la ligne existe. (`lebus+ 13`, présent sur le site, n'est *pas* dans cette liste : il correspond bien à `BDE-13`, déjà dans `routes.txt` — la comparaison le reconnaît correctement.)
- **3/6** : correspond vraisemblablement à `BDE-36` (« Le Jaï - Les Couronnes » dans `routes.txt`, mêmes terminus que « Couronnes <> Jaï » sur le site) — probable écart de nommage (`36` au lieu de `3/6`), pas une ligne manquante. À confirmer avec le réseau avant de coder un mapping.
- **LeBusPRO** : service de transport à la demande pour zones d'activité (Estroublans, Anjoly), sans numéro de ligne. Ne correspond à aucun `route_short_name` du GTFS — les lignes `6000`-`6009` sont nommées `TAD`, `TAD 1`... `TAD 7`, pas `LeBusPRO`. À vérifier si ce service est inclus dans une de ces routes TAD ou totalement absent du GTFS.

### Lignes présentes dans `routes.txt` mais non trouvées sur cette page du site (12)

- **13A**
- **13B**
- **36**
- **6000**
- **6001**
- **6002**
- **6003**
- **6004**
- **6005**
- **6008**
- **6009**
- **ZEN**

Détail : `13A` et `13B` n'ont pas de fiche horaire distincte sur le site (seule `13` y figure) ; `36` n'apparaît nulle part sous ce nom (voir `3/6` ci-dessus) ; `ZEN` (sans lettre) n'a pas de fiche, contrairement à `ZEN A` et `ZEN B` ; les lignes `6000`-`6009` (transport à la demande) ne sont pas sur cette page — probablement publiées ailleurs sur le site (page « transports à la demande »), pas sur la page des fiches horaires de ligne classique.

**Conséquence pour le code à venir** : ne pas construire la liste des lignes valides uniquement depuis `routes.txt` sans vérification humaine — au moins trois lignes réellement en service (2, 3 et 6) en sont absentes. Avant de brancher la recherche de ligne par numéro, confirmer avec le réseau si `routes.txt` est complet ou si le référentiel `mamp` complet (plutôt que `mamp-bde`) comble ce trou.

---

## Synthèse des pièges identifiés

| Piège constaté | Preuve | Conséquence pour le code |
|---|---|---|
| Le jeu expire bientôt | Validité déclarée jusqu'au 20260830, soit dans 20 jours | Le chargeur GTFS doit alerter avant expiration, pas la découvrir en prod. |
| Trois lignes régulières manquent du GTFS | Lignes **2**, **3** et **6** publiées sur le site avec fiche horaire, absentes de `routes.txt` | Ne pas construire le référentiel de lignes uniquement depuis `routes.txt` sans vérification humaine préalable. |
| `city_name` existe mais n'est pas un champ GTFS standard | Colonne propriétaire Mecatran, présente ici mais pas garantie sur un autre réseau | Le code de déduction de commune par coordonnées reste nécessaire pour rester portable — ne pas coder en dur une dépendance à `city_name`. |
| Homonymes de `stop_name` entre communes | « Clinique » apparaît 6 fois, dans 2 communes distinctes (10 noms concernés au total) | La recherche d'arrêt doit toujours désambiguïser par commune, jamais par nom seul. |
| `parent_station` partiel | Seuls 206/666 quais en ont un | Ne pas supposer que deux quais d'un même arrêt physique sont toujours reliés par `parent_station` — certains ne le sont pas. |
| Aucun horaire après minuit dans **ce** jeu | 0 occurrence de `>= 24:00:00` sur 29728 dessertes, max `22:59:00` | Coder quand même le traitement explicite de `>= 24:00:00` : l'absence dans ce jeu d'été ne garantit rien pour le jeu suivant. |
| Pas de lignes scolaires identifiables dans le GTFS | Aucun marqueur trouvé, alors que le site publie des circuits scolaires 590-699 | Vérifier si ces circuits sont hors périmètre `mamp-bde` avant d'affirmer que le réseau n'a pas de lignes scolaires. |
| `wheelchair_boarding` inexploitable | Valeur `0` uniforme sur les 839 arrêts | Ne pas afficher d'information d'accessibilité à partir de ce champ pour ce réseau — la donnée n'existe pas. |

