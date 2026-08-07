# Questions à poser au GTFS

À répondre avant d'écrire la moindre ligne de code applicatif. Chaque réponse doit s'appuyer sur des exemples réels extraits des fichiers, pas sur des généralités.

## Volumétrie
- Combien d'arrêts, de lignes, de courses, de dessertes ?
- Quelle est la période de validité déclarée du jeu ?
- Quels fichiers optionnels sont présents ou absents ?

## Arrêts
- Quel format ont les `stop_id` ? Sont-ils stables d'une version à l'autre ?
- Y a-t-il des `parent_station` regroupant plusieurs quais d'un même arrêt ?
- Combien d'arrêts portent le même `stop_name` ? Lister les dix cas les plus fréquents.
- Les champs `stop_desc`, `zone_id` ou `platform_code` contiennent-ils une indication de commune ?
- Les coordonnées sont-elles toutes renseignées et plausibles ?

## Lignes
- Quel format ont les `route_id` ?
- Quels `route_short_name` sont utilisés ? Y a-t-il des doublons ?
- Le champ `agency_id` distingue-t-il plusieurs marques ou exploitants ?
- Les lignes scolaires sont-elles présentes, et comment les distingue-t-on des lignes régulières ?

## Horaires
- Y a-t-il des `arrival_time` ou `departure_time` au-delà de `24:00:00` ? Combien, et sur quelles lignes ?
- Quelle est l'heure maximale rencontrée ?
- Le fichier `frequencies.txt` est-il présent ? Si oui, quelles courses concerne-t-il ?
- Les `pickup_type` et `drop_off_type` sont-ils utilisés, et pour quoi ?

## Calendriers
- Les services sont-ils décrits par `calendar`, par `calendar_dates`, ou par les deux ?
- Combien de `service_id` distincts ?
- Comment les vacances scolaires sont-elles traitées ?
- Comment les jours fériés sont-ils traités ?
- Y a-t-il des services d'été distincts des services d'année scolaire ?

## Accessibilité et divers
- Le champ `wheelchair_boarding` est-il renseigné ?
- Le fichier `shapes.txt` est-il présent ?
- Y a-t-il des `transfers.txt` entre arrêts ?

## Synthèse attendue
Pour chaque piège identifié, indiquer explicitement la conséquence pour le code à venir. Exemple : « 340 horaires dépassent 24:00:00, tous sur les lignes 9 et 18 — un parsing naïf perdrait les derniers services de ces lignes. »
