# Méthode d'amélioration continue — avec l'équipe CRC

## Pourquoi ce document

Le démonstrateur répond déjà correctement à l'essentiel des questions courantes (tarifs, TAD, objets perdus, amendes — mesuré, pas estimé : voir `tests/questions_evaluation.csv` et `python -m assistant.evalcorpus`). Cette première version a été construite et vérifiée avec des questions que j'ai moi-même imaginées, en m'appuyant sur le site du réseau.

Il manque une chose que je ne peux pas fabriquer moi-même : **ce que les vraies personnes demandent vraiment, avec leurs vrais mots.** C'est exactement ce que l'équipe du CRC sait, et personne d'autre.

Ce document propose une façon simple d'apporter cette connaissance au projet, sans demander à personne de faire un travail technique, et sans jamais faire transiter de donnée d'appel réelle avant que ce soit autorisé.

## Le principe : une phrase, pas une transcription

Quand un membre de l'équipe CRC répond à un appel et se dit *"tiens, si le robot avait eu cet appel, est-ce qu'il aurait su répondre ?"* — ou remarque que l'assistant (une fois testé) a mal compris une formulation — il note **une ligne** :

| Ce que la personne a demandé (reformulé, sans aucune donnée personnelle) | Ce qui aurait dû être répondu |
|---|---|
| « J'ai perdu ma carte Pastel, je fais comment ? » | Contacter l'agence Mobilité — carte remplacée sous 48h |
| « Le bus scolaire de mon fils, il passe à quelle heure au juste ? » | Rediriger vers les horaires théoriques (hors périmètre du corpus documentaire) |

**Aucune transcription, aucun enregistrement, aucun nom, aucun numéro de téléphone.** La personne qui note reformule de mémoire, comme elle le ferait pour expliquer un cas à un collègue. C'est ce geste de reformulation — fait par un humain, dans l'instant — qui évite d'avoir besoin d'une AIPD et de l'accord du DPO : aucune donnée de voyageur ne sort jamais de la tête de la personne qui a pris l'appel.

C'est délibérément la même limite que celle déjà posée à l'Étape 7 de la méthode de développement (*« Aucune donnée de voyageur : le DPO n'est pas encore dans la boucle »*) : ce projet n'a pas attendu cette étape pour commencer à apprendre de l'équipe CRC, il respecte juste la même règle plus tôt.

## L'outil : le même que celui qui a servi à construire la v0

Rien de nouveau à apprendre. C'est le fichier `tests/questions_crc.csv`, qui se remplit comme un tableur (une ligne = une question), et se mesure avec la commande déjà construite :

```
uv run python -m assistant.evalcorpus tests/questions_crc.csv
```

Elle affiche, question par question, si l'assistant aurait trouvé la bonne page — et un taux de réussite global, comparable dans le temps.

Concrètement, trois façons possibles d'alimenter ce fichier, du plus simple au plus outillé :
1. **Un tableur partagé** (Google Sheets, Excel) où l'équipe CRC ajoute une ligne au fil de l'eau ; une fois par semaine, quelqu'un du projet le recopie dans `tests/questions_crc.csv`.
2. **Directement le fichier CSV**, pour qui est à l'aise avec GitHub.
3. **Une réunion courte** (15 min, une fois par semaine) où l'équipe CRC raconte les cas rencontrés, notés en direct.

Les trois font le même travail. Le premier est le plus simple pour démarrer.

## Ce que ça révèle, et comment on corrige

Chaque échec se range dans une des trois cases suivantes — c'est la distinction qui a servi tout au long de la construction de la v0, et elle continue de s'appliquer :

- **Trou de vocabulaire** : la réponse existe dans le corpus, mais sous un autre nom que celui de l'appelant (« carnet » vs « TITRE 10 VOYAGES », déjà rencontré). Correction rapide et sans risque : on ajoute le nom courant à côté du nom officiel dans le corpus.
- **Trou de contenu** : la réponse n'existe nulle part sur le site, donc nulle part dans le corpus. Ça ne se corrige pas dans le code : il faut soit l'ajouter au site (en dehors du périmètre de ce projet), soit l'ajouter à `data/connaissances.md`, la base de connaissance écrite à la main prévue pour ça.
- **Vraie question hors périmètre** : la question ne relève pas de `rechercher_information` (horaires, réclamation nécessitant un humain, etc.) — la bonne réponse est alors « transférer vers un agent », pas une page.

Cette distinction, une fois faite, se règle en général en quelques minutes par cas — sauf le trou de contenu, qui dépend de ce que contient déjà le site.

## Pour aller plus loin (plus tard, avec le DPO)

Si l'équipe veut un jour aller au-delà de la reformulation manuelle — par exemple faire analyser automatiquement de vraies transcriptions d'appels pour repérer les questions mal comprises à grande échelle — c'est possible, mais ça change de nature : ça touche de la donnée de voyageur réelle, et ça suit alors le même chemin que l'ouverture aux voyageurs (Étape 7) : AIPD allégée, accord du DPO, anonymisation vérifiée avant tout traitement. Rien de ça n'est nécessaire pour démarrer avec la méthode ci-dessus — ce n'est à envisager que si le volume de retours manuels devient trop faible pour progresser, ce qui n'arrivera pas avant longtemps vu la taille du corpus actuel.

## En résumé, pour l'équipe CRC

- Vous n'avez rien à installer, rien à coder.
- Une ligne, une question reformulée, jamais de donnée personnelle.
- Ce que vous remontez est mesuré automatiquement, pas laissé de côté.
- Vous êtes, très concrètement, celles et ceux qui rendent cet assistant meilleur.
