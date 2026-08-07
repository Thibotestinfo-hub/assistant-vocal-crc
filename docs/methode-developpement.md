# Méthode de développement — démonstrateur assistant vocal

Construit par toi, avec Claude Code. Sept étapes, chacune se terminant par quelque chose qui fonctionne et que tu peux constater.

**Charge estimée** : 15 à 20 journées de travail effectif, étalées sur 6 à 8 semaines.

---

## Règles de travail

**Une session Claude Code = un objectif.** Jamais « construis-moi l'application ». Toujours « ajoute la fonction X, avec un script qui me permet de vérifier qu'elle marche ».

**Un commit git à chaque état qui fonctionne.** Avant de demander une modification importante, commit. C'est ta seule assurance.

**N'accepte jamais du code que tu ne peux pas résumer en une phrase.** Si tu ne comprends pas ce qu'un fichier fait, demande l'explication avant de continuer. Le jour où quelque chose cassera en production, tu seras seul devant.

**Chaque fonction s'accompagne d'un script de vérification.** Demande-le systématiquement. C'est ce qui te permettra plus tard de modifier le prompt sans casser silencieusement autre chose.

**Les secrets dans un fichier `.env`, jamais dans le dépôt.** Vérifie que `.env` est bien dans le `.gitignore` avant le premier commit.

**Déploie tôt.** À l'étape 3, mets en ligne une API qui ne fait rien d'autre que répondre « bonjour ». Les problèmes de déploiement se découvrent toujours au pire moment ; autant les rencontrer quand il n'y a rien à perdre.

---

## Étape 0 — Le socle (une demi-journée)

**Objectif** : un dépôt, un environnement de travail accessible, et les documents de référence en place.

Tout se fait dans le navigateur, sans rien installer.

1. Vérifie que `github.com` et `claude.ai/code` sont accessibles depuis ton poste. Si l'un des deux est filtré par la DSI, arrête-toi là et fais la demande d'ouverture.
2. Crée un compte GitHub et un dépôt **privé** `assistant-vocal-crc`, en cochant « Add a README file ».
3. Dépose les documents via l'interface web de GitHub, par glisser-déposer : `CLAUDE.md` à la racine, et `spec-assistant-vocal-v0-revisee.md`, `methode-developpement.md`, `questions-gtfs.md` dans un dossier `docs/`.
4. Crée le `.gitignore` directement dans l'interface web, avec au minimum `.env`, `data/gtfs/`, `data/corpus/`, `*.db`, `__pycache__/`, `.venv/`.
5. Connecte le dépôt à Claude Code sur le web et autorise l'accès réseau du bac à sable à `transport.data.gouv.fr` et au domaine du site du réseau.

**Livrable** : une première session Claude Code qui voit le dépôt et son `CLAUDE.md`.

**Point de vigilance** : vérifie que le `.gitignore` est en place avant tout ajout de fichier. Une clé d'API poussée sur GitHub reste dans l'historique même après suppression.

**En parallèle** : ouvre un compte Twilio et achète un numéro américain ou britannique, disponible immédiatement et sans dossier réglementaire. Le numéro français en 04 exige un KBis et l'identité d'un dirigeant : ce dossier se lancera à la rentrée, et le numéro ne sera nécessaire qu'à l'étape 7.

---

## Étape 1 — Comprendre le GTFS (1 à 2 jours)

**Objectif** : savoir exactement ce qu'il y a dans les données, avant d'écrire quoi que ce soit qui s'appuie dessus.

Télécharge le GTFS `mamp-bde` depuis transport.data.gouv.fr, décompresse, et fais-toi un état des lieux. Les questions auxquelles tu dois pouvoir répondre :

- Quel format ont les `stop_id` et les `route_id` ?
- Les arrêts homonymes de communes différentes ont-ils des identifiants distincts ?
- Y a-t-il des `parent_station` regroupant plusieurs quais d'un même arrêt ?
- Comment les vacances scolaires sont-elles traitées : `calendar`, `calendar_dates`, ou des `service_id` séparés ?
- Y a-t-il des horaires au-delà de `24:00:00` ? Combien ?
- Combien d'arrêts, de lignes, de courses ?

**Livrable** : un document `docs/fiche-gtfs.md` de deux pages répondant à ces questions, avec des exemples réels extraits du fichier.

**Difficulté attendue** : aucune technique, mais c'est l'étape qu'on est tenté de sauter. Ne la saute pas. Toutes les mauvaises surprises du projet sont dans ces fichiers, et il vaut mieux les découvrir maintenant que dans six semaines.

**Prompt de session** :
> Voici le GTFS du réseau, décompressé dans `data/gtfs/`. Écris un script d'exploration qui produit un rapport en markdown répondant aux questions listées dans `docs/questions-gtfs.md`. Ne construis rien d'autre pour l'instant : je veux d'abord comprendre les données. Montre-moi des exemples concrets extraits des fichiers, pas des statistiques générales.

---

## Étape 2 — La base et l'ingestion (2 à 3 jours)

**Objectif** : une base SQLite alimentée par le GTFS, et un script en ligne de commande qui répond à « prochain 9 aux Pinchinades ».

Trois choses à construire :

1. Le schéma et le chargeur GTFS, avec un traitement explicite des heures au-delà de minuit
2. L'enrichissement des arrêts par leur commune, déduite des coordonnées et du contour des communes (contours disponibles en open data)
3. L'index phonétique et la recherche d'arrêt

**Livrable** : une commande `python -m assistant.cherche "pinchinade"` qui renvoie les bons candidats, et `python -m assistant.horaires <stop_id> --type dernier` qui renvoie le bon horaire — vérifié à la main contre la fiche horaire du site.

**Difficultés attendues** :

- *Les heures au-delà de minuit.* Un départ à 0h30 s'écrit `24:30:00`. Traite-les explicitement, et vérifie que les derniers services de la journée remontent bien.
- *La commune.* Le GTFS ne la contient pas. Il faut la calculer géographiquement. Vérifie le résultat sur une vingtaine d'arrêts que tu connais.
- *Le matching phonétique.* C'est le poste le plus long. Commence par une combinaison recherche floue plus code phonétique, puis constitue une liste de 100 prononciations réelles pour mesurer. N'espère pas régler ça en une session : c'est un cycle mesure-ajustement qui durera tout le projet.

**Prompt de session, à découper en trois sessions distinctes** :
> Session A : construis le schéma SQLite et le script de chargement du GTFS. Traite explicitement les heures au-delà de 24:00:00 — explique-moi comment tu les gères avant de coder. Ajoute un script de vérification qui compare, pour trois lignes que je te donnerai, les premiers et derniers départs calculés avec les fiches horaires officielles.

---

## Étape 3 — L'API des outils, en ligne (2 jours)

**Objectif** : les fonctions de la spec exposées en HTTP, accessibles depuis internet, authentifiées, et rapides.

Commence par déployer une API vide qui répond « bonjour ». Une fois qu'elle est en ligne et joignable, ajoute les endpoints un par un.

**Livrable** : tu appelles ton API depuis ton téléphone et tu obtiens une réponse en moins de 300 ms.

**Difficultés attendues** :

- *Le premier déploiement.* HTTPS, variables d'environnement, journalisation. Compte une demi-journée de tâtonnement, c'est normal.
- *La latence.* Ton API sera dans le chemin critique de la conversation. Chaque endpoint doit répondre sous 300 ms. Mesure-le, ne le suppose pas.
- *Le sommeil des instances.* Vérifie que ton hébergement ne met pas l'application en veille après quelques minutes d'inactivité.

**Prompt de session** :
> Expose les outils décrits dans `docs/spec-assistant-vocal-v0-revisee.md`, section 4, en endpoints FastAPI. Un jeton bearer en en-tête pour l'authentification. Chaque endpoint renvoie exactement le format JSON décrit dans la spec. Ajoute un script de test qui appelle chaque endpoint et vérifie le format et le temps de réponse.

---

## Étape 4 — Le pipeline documentaire (2 à 3 jours)

**Objectif** : ingérer automatiquement le site du réseau, et savoir mesurer si la recherche documentaire est bonne.

Aucune rédaction manuelle de réponses. Le pipeline doit pouvoir être relancé à volonté — notamment quand le site sera enrichi de nouveaux documents.

### 4a — Extraction

- Découverte des URL : `sitemap.xml` si présent, sinon parcours du site restreint au domaine
- Extraction du contenu principal en markdown, avec titre, URL et date d'extraction en en-tête
- Les PDF sont inclus, **sauf les fiches horaires**, exclues par motif d'URL : les horaires viennent du GTFS et une fiche horaire mal extraite produit des réponses fausses
- Sortie : un fichier markdown par page dans `data/corpus/`

**Difficultés attendues** :

- *Le rendu JavaScript.* Vérifie d'abord si les pages sont servies complètes. Si le contenu n'apparaît qu'après exécution du script, il faudra un navigateur sans interface pour l'extraction, ce qui alourdit nettement le pipeline.
- *Les tarifs en tableau ou en image.* C'est le cas le plus dangereux : un tarif présenté en image disparaît silencieusement du corpus, et l'assistant répondra qu'il ne sait pas — ou pire, approximera. D'où le contrôle de l'étape 4c.
- *Le bruit de navigation.* Menus, pieds de page et fils d'Ariane répétés sur chaque page polluent la recherche. Il faut les retirer à l'extraction.

### 4b — Indexation et recherche

- Découpage par section, en s'appuyant sur les titres, 400 à 800 mots par bloc
- Chaque bloc conserve le titre de la page, son URL et sa date
- Vectorisation par un service européen ou un modèle local
- Stockage en mémoire, chargé au démarrage : quelques centaines de blocs ne justifient aucune base vectorielle
- `rechercher_information` renvoie les 5 blocs les plus proches, avec leurs sources et leur score. **Aucun appel de modèle supplémentaire à cette étape** : c'est l'agent vocal qui formule, ce qui évite d'ajouter une demi-seconde au chemin critique
- En dessous d'un score plancher, l'outil renvoie `trouve: false` plutôt qu'un bloc hors sujet

### 4c — L'évaluation, qui remplace le travail manuel

C'est ici que se joue l'exactitude.

Constitue une liste d'environ 50 questions réelles, avec pour chacune la page qui devrait répondre. Une à deux heures de travail. **Demande-les à l'équipe CRC dès son retour** : ce sont eux qui savent ce qu'on leur demande vraiment, et c'est un excellent point d'entrée pour les associer au projet.

Puis un script qui, pour chaque question, vérifie que la bonne page ressort dans les 5 blocs retournés. La mesure est un taux de succès. **Vise 90 % minimum avant de brancher quoi que ce soit.**

Ajoute un contrôle de complétude : un script qui liste tous les montants en euros trouvés dans le corpus. Tu le parcours en deux minutes, et tu vois immédiatement si la grille tarifaire a été correctement extraite ou si elle s'est perdue dans une image.

**Livrable** : `python -m assistant.evalcorpus` affiche un taux de succès, et `python -m assistant.demande "c'est combien un carnet"` renvoie les bons blocs avec leurs sources.

### 4d — Rafraîchissement

Une commande `python -m assistant.corpus --refresh` qui relance l'extraction et produit un rapport des différences : pages ajoutées, modifiées, disparues. À lancer chaque semaine, et à chaque enrichissement du site.

---

## Étape 5 — L'agent vocal (2 à 3 jours)

**Objectif** : tu appelles un numéro et ça répond correctement.

Configuration sur la plateforme vocale : voix, modèle, prompt système de la spec, déclaration des outils pointant vers ton API, numéro entrant.

**Livrable** : le premier appel réussi. C'est le moment où le projet devient réel.

**Difficultés attendues** :

- *Le format des outils.* Chaque plateforme a ses conventions de déclaration et de webhook. Compte une demi-journée pour comprendre la leur.
- *La prononciation.* Les noms d'arrêts locaux seront massacrés. Il faut un dictionnaire de prononciation, construit à l'oreille, arrêt par arrêt.
- *Le réglage des interruptions.* Trop sensible, l'agent se coupe au moindre « mmh ». Pas assez, il parle par-dessus l'appelant. C'est un curseur à régler en appelant, pas en lisant la documentation.
- *La latence de bout en bout.* Mesure-la sur chaque appel. Si elle dérape, le coupable est presque toujours ton API ou un outil appelé inutilement.

---

## Étape 6 — Le back-office (2 à 3 jours)

**Objectif** : voir les appels, exporter les données, reprendre la main.

Dans cet ordre strict, sans jamais laisser le suivant bloquer le précédent :

1. **L'historique.** Un webhook de fin d'appel enregistre en base : horodatage, durée, transcription, résumé, intention, statut, coût, modèle, tokens. Une page web qui liste tout ça.
2. **Les exports.** Objets perdus, demandes de rappel, contacts collectés avec leurs consentements. En CSV.
3. **La transcription en direct.** Un websocket depuis la plateforme vers une page qui affiche la conversation en cours.
4. **La reprise en main.** Un bouton qui transfère l'appel vers un mobile en affichant le résumé.

**Difficulté attendue** : les points 3 et 4 sont la partie la plus difficile du projet. Si tu bloques, arrête-toi au point 2 : un démonstrateur sans reprise en main en direct reste parfaitement convaincant, et tu pourras le présenter comme la prochaine brique.

---

## Étape 7 — Les tests (2 semaines)

1. **Toi seul**, contre le jeu de test de la spec, section 6. Tu vérifies chaque réponse contre la source. Tu itères.
2. **Six à huit collègues**, avec des fiches de scénario, depuis leurs propres téléphones. Aucune donnée de voyageur : le DPO n'est pas encore dans la boucle et c'est ce qui te laisse cette marge.
3. **Ouverture aux voyageurs** — mais seulement après l'AIPD allégée et l'accord du DPO.

**Difficulté attendue** : chaque correction du prompt peut casser un cas qui marchait. D'où le jeu de test rejoué intégralement à chaque modification. C'est fastidieux, et c'est ce qui te permettra de tenir 95 % d'exactitude devant un CoDir.

---

## Récapitulatif des comptes à ouvrir

| Service | Usage | Coût |
|---|---|---|
| GitHub | dépôt privé | gratuit |
| Scaleway ou Clever Cloud | API + back-office | ~15 €/mois |
| Plateforme vocale | agent conversationnel | à l'usage |
| Opérateur téléphonique | numéro entrant | ~10 €/mois |
| Fournisseur SMS | envois | à l'usage |

---

## Par quoi commencer aujourd'hui

Trois actions, dans cet ordre.

1. **Ouvre un compte télécom et achète un numéro étranger** — quelques euros, disponible immédiatement, suffisant pour tout le développement. Le numéro français demande un KBis et se lancera à la rentrée.
2. **Crée le dépôt** et dépose dedans le `CLAUDE.md` et la spec.
3. **Télécharge le GTFS** et ouvre ta première session Claude Code avec le prompt de l'étape 1.

Et une quatrième, non technique, qui pèsera autant que les trois autres : **écris à la responsable du CRC** pour lui proposer, à son retour, une heure d'échange sur les motifs d'appel. Pas pour valider le projet — pour qu'elle en soit co-auteure dès le début.
