# Sources de données du projet

Vérifié le 06/08/2026 sur transport.data.gouv.fr.

---

## GTFS statique — priorité 1

### Les bus de l'étang (périmètre exact du POC)

```
https://app.mecatran.com/utw/ws/gtfsfeed/static/mamp-bde?apiKey=2b7a3b3b084c750566663c2e09726b19171f275c
```

Dessert Berre-l'Étang, Gignac-la-Nerthe, Les Pennes-Mirabeau, Marignane, Rognac, Saint-Victoret, Velaux, Vitrolles.

- Validité déclarée : **06/07/2026 → 30/08/2026**
- 21 avertissements à la validation
- Page de détail : https://transport.data.gouv.fr/resources/39597

⚠️ Expire le 30/08/2026, veille de la nouvelle offre du réseau. À surveiller.

### Référentiel complet (tous les réseaux métropolitains)

```
https://app.mecatran.com/utw/ws/gtfsfeed/static/mamp?apiKey=60327e505a214c77303f52206f11483069257343
```

- Validité déclarée : **05/08/2026 → 22/02/2027**
- 1 075 avertissements à la validation
- Page de détail : https://transport.data.gouv.fr/resources/81969

Alternative plus durable, à filtrer par agence pour ne garder que le périmètre Étang. À évaluer après l'exploration.

### Jeux voisins, susceptibles de compléter le périmètre

| Réseau | URL |
|---|---|
| Côte Bleue | `https://app.mecatran.com/utw/ws/gtfsfeed/static/mamp-ctb?apiKey=686525656f2c3228054e6a7c3e38330037076207` |
| CG13 Cartreize (lecar, navettes aéroport) | `https://app.mecatran.com/utw/ws/gtfsfeed/static/mamp-c13?apiKey=3675433c4f196f4d3c6b62316e130536196f0336` |
| Libébus (zone Salon, hors périmètre) | `https://app.mecatran.com/utw/ws/gtfsfeed/static/mamp-lib?apiKey=14276f6a093c2c53370b48001f75646f2b2c3969` |

---

## Temps réel — reporté en v1

### SIRI Bus de l'Étang

```
https://siri.lametropolemobilite.fr/BDE_URB
```

- `requestor_ref` pour l'open data : `open-data`
- Taux de disponibilité mesuré par le PAN : **76,6 %**
- Statut au 06/08/2026 : **non disponible**
- Outil de test sans code : https://transport.data.gouv.fr/tools/siri-querier

### Perturbations — GTFS-RT Service Alerts

```
https://api-mobilite.rbgl.fr/api/v1/mamp/getServiceAlerts
```

Ressource communautaire agrégeant les perturbations de tous les réseaux métropolitains depuis M DATA. Format Protocol Buffers, rafraîchissement toutes les 5 minutes, mode FULL_DATASET.

Contenu par alerte : période de validité, `routeId` et `stopId` ciblés, `cause` et `effect` normalisés, `headerText` et `descriptionText` en français.

- Documentation : https://api-mobilite.rbgl.fr/api-docs/#/MAMP/get_api_v1_MAMP_getServiceAlerts
- Source amont officielle : https://data.ampmetropole.fr/explore/dataset/ol-perturbation-la-mobilite

⚠️ Ressource tierce, non officielle. Acceptable pour le démonstrateur, à remplacer par la source AMP pour le pilote.

---

## Corpus documentaire — étape 4

Site du réseau : https://www.salonetangcotebleue.fr/

Le site est généré par Cityway. À vérifier lors de l'extraction : rendu serveur ou JavaScript, présence d'un `sitemap.xml`, et chemin du flux RSS des infos trafic, accessible depuis la page infos trafic.

**À exclure de l'ingestion** : les fiches horaires en PDF. Les horaires viennent du GTFS.

---

## Domaines à autoriser dans le bac à sable

```
app.mecatran.com
transport.data.gouv.fr
www.salonetangcotebleue.fr
api-mobilite.rbgl.fr
siri.lametropolemobilite.fr
```

---

## Contexte réglementaire

Licence Ouverte 2.0 pour l'ensemble des jeux GTFS et SIRI. Données publiées par la Métropole d'Aix-Marseille-Provence, service opéré par La Métropole Mobilité.
