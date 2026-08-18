# Projet — Assistant vocal CRC, zone Étang

## Contexte

Démonstrateur d'assistant téléphonique pour un réseau de bus de la zone Étang de Berre. Il répond aux appels de voyageurs sur les tarifs, les horaires théoriques et les déclarations d'objets perdus. Il n'est branché à aucun système métier : les données viennent de l'open data et d'une base de connaissance écrite à la main.

La spécification fonctionnelle complète est dans `docs/spec-assistant-vocal-v0-revisee.md`. **Elle fait autorité.** En cas de contradiction entre ce fichier et la spec, c'est la spec qui gagne.

## Qui je suis

Je ne suis pas développeur. J'ai des bases techniques solides et j'ai déjà mené un projet applicatif avec toi, mais je dois pouvoir comprendre et maintenir seul ce qu'on écrit.

En conséquence :

- Explique-moi ce que tu vas faire avant de le faire, en quelques phrases
- Préfère toujours la solution la plus simple qui marche à la plus élégante
- Pas d'abstraction anticipée : on résout le problème d'aujourd'hui
- Commente le code là où l'intention n'est pas évidente à la lecture
- Si je te demande quelque chose qui me mènera dans un mur, dis-le-moi

## Stack

- Python 3.11+, environnement géré par `uv`
- SQLite pour toutes les données — pas de PostgreSQL
- FastAPI pour l'API des outils et le back-office
- Pas de base vectorielle, pas de framework front, pas de Docker tant que ce n'est pas nécessaire
- Hébergement européen

## Contraintes non négociables

**Latence.** Chaque endpoint de l'API répond en moins de 300 ms. Cette API est dans le chemin critique d'une conversation téléphonique.

**Exactitude.** L'assistant n'énonce jamais une information qui ne vient pas d'une source vérifiable. Aucune valeur en dur dans le code, aucune approximation, aucun repli sur une réponse plausible. Si la donnée manque, la réponse est « je ne sais pas » et l'appel bascule vers un humain.

**Vérifiabilité.** Toute fonction s'accompagne d'un moyen simple de vérifier qu'elle donne le bon résultat, comparé à la source officielle.

**Traçabilité.** Chaque appel logge le modèle utilisé, les tokens consommés, les minutes de reconnaissance et de synthèse vocale, et le coût estimé. Ces données servent à l'évaluation économique et environnementale du projet, elles ne sont pas reconstituables après coup.

**Paramétrage.** Tout ce qui est propre à ce réseau vit dans un fichier de configuration : source GTFS, périmètre géographique, horaires d'ouverture, identité vocale, numéros. Le code ne doit rien contenir de spécifique à ce réseau — l'agent devra pouvoir être dupliqué ailleurs par simple paramétrage.

## Structure du dépôt

```
assistant/          code applicatif
  ingestion/        chargement GTFS, enrichissement, index phonétique
  outils/           les fonctions exposées à l'agent
  api/              FastAPI
  backoffice/       suivi des appels et exports
data/
  gtfs/                 GTFS décompressé, non versionné
  connaissances.md      base de connaissance écrite à la main
  config.yaml           paramètres du réseau
  corpus_index.json     index documentaire + embeddings, versionné (voir pièges connus)
docs/               spec, fiche GTFS, notes
tests/              jeu de test et scripts de vérification
```

## Pièges connus de ce projet

- Le GTFS contient des heures au-delà de `24:00:00` (par exemple `24:30:00` pour un départ à 0h30). Tout traitement naïf perd les derniers services de la journée, qui sont précisément ceux qui nous intéressent.
- Le GTFS ne contient **pas** de champ commune. Elle doit être déduite des coordonnées de l'arrêt. Elle est indispensable pour lever l'ambiguïté entre arrêts homonymes.
- Les numéros de ligne se répètent d'une zone à l'autre du réseau et d'une marque à l'autre. Toute recherche par numéro doit être bornée au périmètre configuré.
- Le GTFS a une période de validité et expire. Le chargeur doit alerter quand la fin de validité approche.
- Les noms d'arrêts locaux sont difficiles à reconnaître à l'oral. Le matching phonétique est un cycle mesure-ajustement continu, pas un problème qu'on règle une fois.
- `data/` est ignoré par Git presque en entier, sauf `data/corpus_index.json` : ce fichier est le résultat d'un calcul lent (téléchargement + calcul d'un modèle d'embeddings), et rien n'est conservé d'un déploiement Clever Cloud à l'autre. Sans le versionner, ce calcul recommence à chaque déploiement, au risque de dépasser le délai du health-check. Après tout `assistant.corpus --refresh` suivi d'un `indexer_corpus`, il faut recommitter ce fichier.

## Méthode de session

Une session, un objectif. Termine chaque session par un état qui fonctionne et que je peux constater moi-même en lançant une commande.

Avant toute modification importante, rappelle-moi de committer.
