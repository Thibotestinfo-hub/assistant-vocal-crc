# Dossier d'audit DSI — Assistant vocal, zone Étang

Document en construction, chapitre par chapitre, pour l'audit interne DSI précédant un pilote public sur une filiale. Structure complète et méthode de rédaction actées avec l'utilisateur le 29/09/2026 (voir `docs/prochaines-etapes.md`).

Chaque affirmation de ce document vient d'un fichier réel du dépôt, du code lui-même, ou d'une vérification technique directe. Quand un fait ne peut pas être vérifié depuis le dépôt seul (contrats fournisseurs, localisation exacte de serveurs tiers...), il est marqué **[À vérifier — DSI/DPO]** plutôt qu'affirmé.

Statut : parties 1 à 8 rédigées. Annexes à venir.

---

## Partie 1 — Intention et genèse

### 1.1 Résumé exécutif

Reprise textuelle du contexte tel que défini dans `CLAUDE.md`, le document de référence du projet. Précision utile pour la lecture de ce document : `CLAUDE.md` n'est pas un texte que l'assistant IA s'est écrit à lui-même — chaque règle qu'il contient (hébergement européen, pas de donnée inventée, budget de latence de 300 ms, etc.) a été dictée par l'utilisateur, qui a ensuite demandé qu'elle soit consignée par écrit pour s'appliquer de façon systématique à tout le code produit par la suite. Les décisions de cadrage viennent de l'utilisateur ; leur mise en œuvre technique vient de Claude Code.

> Démonstrateur d'assistant téléphonique pour un réseau de bus de la zone Étang de Berre. Il répond aux appels de voyageurs sur les tarifs, les horaires théoriques et les déclarations d'objets perdus. Il n'est branché à aucun système métier : les données viennent de l'open data et d'une base de connaissance écrite à la main.

Ce dernier point est structurant pour l'audit : l'assistant ne lit ni n'écrit dans aucun système d'information existant (billettique, CRM, planification) — son seul état propre est la petite base SQLite décrite en Partie 2, et ses seules sources externes sont des données ouvertes (GTFS, site public du réseau).

### 1.2 Genèse et méthode de conception

Ce projet a été construit par l'utilisateur lui-même, non-développeur de profession, avec Claude Code comme assistant de développement — un choix assumé et documenté dès l'origine (`docs/methode-developpement.md`), pas découvert a posteriori. La méthode retenue, écrite avant la première ligne de code, repose sur des règles de travail explicites :

- **Une session de travail = un objectif** — jamais une demande ouverte du type « construis l'application ».
- **Un commit à chaque état qui fonctionne**, pour toujours pouvoir revenir en arrière.
- **« N'accepte jamais du code que tu ne peux pas résumer en une phrase »** — condition explicite pour que l'utilisateur reste en mesure de maintenir seul ce qui est écrit pour lui, une fois le projet livré.
- **Chaque fonction s'accompagne d'un script de vérification** — pas de confiance aveugle dans le code produit, une vérification systématique.
- **Déployer tôt** — une API en ligne dès l'étape 3 de la méthode, avant même que les fonctionnalités ne soient complètes, pour rencontrer les problèmes d'infrastructure quand il n'y a encore rien à perdre.

Le développement s'est déroulé par itérations courtes et vérifiées, documentées au fil de l'eau dans `docs/prochaines-etapes.md` (le journal de bord complet du projet, plusieurs centaines d'entrées datées) — la Partie 4.4 de ce document en reprend les épisodes les plus significatifs pour l'audit.

### 1.3 Périmètre fonctionnel actuel

L'assistant répond aujourd'hui sur six familles de sujets, chacune correspondant à un ou plusieurs outils détaillés en Partie 3 :

1. **Horaires théoriques** — prochains passages ou créneau horaire à un arrêt donné.
2. **Informations commerciales et pratiques** — tarifs, abonnements, vélo en libre-service, transport à la demande, amendes, à partir d'une base de connaissance indexée depuis le site public du réseau.
3. **Objets perdus** — déclaration complète (nature, description, ligne, date, lieu, coordonnées).
4. **Demande de rappel** — vers un conseiller humain, pour tout sujet hors périmètre automatisable.
5. **Itinéraire** — trajet théorique direct ou avec une correspondance via le moteur propre du projet ; en repli, quand celui-ci ne trouve rien, un trajet plus complexe calculé par un service externe (Google Routes API), avec une préférence optionnelle (moins de marche ou moins de correspondances) si l'appelant l'exprime ; envoi du détail par SMS (Twilio) à la demande de l'appelant. **Chacun de ces trois éléments est une fonctionnalité expérimentale désactivée par défaut**, avec son propre interrupteur back-office (Partie 3, Partie 7.2).
6. **Sortie vers un humain** — transfert ou rappel systématique dès que l'assistant ne sait pas répondre, jamais d'invention.

Aucun horaire ou tarif temps réel : tout est présenté comme prévu, jamais comme garanti — choix assumé dans le prompt de l'agent, cohérent avec l'absence de connexion à un système métier (1.1).

### 1.4 État d'avancement

Le projet a passé son test interne (démonstration à l'équipe CRC) et pourrait devenir, sous réserve de cet audit, un pilote public sur une filiale du groupe — un test grandeur réelle, mais toujours sans développement lourd supplémentaire. C'est le contexte précis de ce document : documenter exhaustivement l'existant pour que la DSI puisse se prononcer en connaissance de cause, plutôt que de laisser le POC continuer à vivre sans traçabilité formelle de ses choix.

### 1.5 Ce que ce document couvre

Architecture et choix techniques (Partie 2), inventaire complet des outils exposés à l'agent (Partie 3), organisation et anomalies connues du code (Partie 4), sécurité (Partie 5), RGPD et données personnelles (Partie 6), traçabilité et gouvernance (Partie 7), perspective ouverte sur un déploiement public sécurisé (Partie 8). Il ne couvre pas les aspects contractuels et organisationnels qui ne se lisent pas dans le dépôt de code (accords de sous-traitance RGPD, conditions contractuelles des fournisseurs) — signalés partout où c'est pertinent comme **[À vérifier — DSI/DPO]**.

---

## Partie 2 — Architecture et choix techniques

### 2.1 Vue d'ensemble

Un appel suit ce trajet :

1. **L'appelant** compose le numéro du réseau.
2. **Twilio** (opérateur téléphonique) reçoit l'appel et le relie à l'agent conversationnel ElevenLabs.
3. **ElevenLabs** assure la reconnaissance vocale (ASR), orchestre le modèle de langage (LLM — actuellement Gemini 3.1 Flash Lite) qui décide quoi dire et quels outils appeler, et synthétise la réponse vocale (TTS).
4. Quand l'agent a besoin d'une donnée réelle (horaire, tarif, arrêt...), ElevenLabs appelle un **outil** : une requête HTTP vers notre API, hébergée sur **Clever Cloud**.
5. Notre API interroge une base **SQLite** (données GTFS statiques, régénérées à chaque déploiement) ou une autre base SQLite (état applicatif persistant : déclarations d'objets perdus, demandes de rappel, activation des outils), et répond en JSON.
6. En fin d'appel, ElevenLabs envoie un **webhook** (`/webhooks/elevenlabs/fin_appel`) contenant la transcription complète, les métriques d'usage (modèle, tokens, coût, minutes voix) et l'audio, que nous enregistrons pour la traçabilité et le suivi qualité (voir Partie 7).

Aucune donnée ne transite par un autre service que ceux listés en 2.4 : pas de base de données tierce, pas d'analytics externe, pas de stockage cloud générique.

### 2.2 Stack technique et justification

| Brique | Choix | Version minimale | Pourquoi |
|---|---|---|---|
| Langage | Python | 3.11+ | Écosystème mature pour l'ingestion de données (GTFS), API légère, maintenable par une équipe réduite. |
| Gestionnaire d'environnement | [uv](https://docs.astral.sh/uv/) | — | Installation reproductible et rapide, un seul outil pour dépendances + exécution, pas de configuration supplémentaire (Poetry, pip-tools...). |
| API | [FastAPI](https://fastapi.tiangolo.com/) | 0.141+ | Validation automatique des entrées/sorties par schémas typés (Pydantic) — chaque paramètre d'outil est validé avant d'atteindre le code métier, ce qui a concrètement bloqué des données invalides envoyées par un modèle de langage lors des tests du 28/09/2026 (voir Partie 4.4). Documentation interactive générée automatiquement (`/docs`), utile pour l'audit lui-même. |
| Serveur applicatif | [Uvicorn](https://www.uvicorn.org/) | 0.52+ | Serveur ASGI standard pour FastAPI, pas de choix alternatif nécessaire à cette échelle. |
| Base de données | SQLite | — | Un seul fichier par base, pas de serveur de base de données à administrer ni à sécuriser séparément. Explicitement préféré à PostgreSQL dans les règles du projet (`CLAUDE.md`) tant que le volume ne le justifie pas — un POC à l'échelle d'un réseau de bus ne dépasse pas ce que SQLite gère confortablement. Deux bases distinctes : `data/gtfs.db` (horaires, arrêts — régénérée à chaque déploiement depuis la source GTFS, aucune donnée personnelle) et `data/etat/assistant.db` (état applicatif persistant : déclarations, demandes de rappel, activation des outils — contient les données personnelles, voir Partie 6). |
| Recherche floue (noms d'arrêts) | [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) | 3.14+ | Correspondance phonétique/orthographique tolérante aux hésitations et déformations de la reconnaissance vocale (« Émile Ripert » entendu correctement malgré une prononciation approximative). Bibliothèque locale, aucun appel réseau. S'ajoute à un traitement propre au projet : `assistant/cherche.py` combine RapidFuzz à un code phonétique calculé pour chaque nom d'arrêt (regroupement des sons proches, au-delà de la simple orthographe) — les deux mécanismes sont complémentaires, pas redondants. |
| Extraction de contenu web | BeautifulSoup4, markdownify | — | Première étape du pipeline de base de connaissance : transforme les pages du site public du réseau en fichiers Markdown bruts (hors ligne, pas exposée à l'agent en direct). |
| Indexation documentaire | [fastembed](https://github.com/qdrant/fastembed) | 0.8+ | Deuxième étape, sur le résultat de l'étape précédente : calcule des embeddings pour la recherche dans la base de connaissance (tarifs, FAQ). Modèle exécuté localement, pas d'appel à une API d'embeddings tierce — le résultat est un fichier JSON versionné (`data/corpus_index.json`), pas une base vectorielle à part entière (explicitement écarté par les règles du projet, jugée disproportionnée à cette échelle). |
| Calcul géographique | Shapely | 2.1+ | Déduction de la commune d'un arrêt à partir de ses coordonnées (le GTFS source ne fournit pas ce champ — piège connu du projet, voir `CLAUDE.md`). |
| Client HTTP | httpx | 0.28+ | Appels sortants (API Adresse du gouvernement pour le géocodage, API ElevenLabs pour la gestion des voix). |
| Configuration réseau | YAML (`data/config.yaml`) | — | Tout ce qui est propre à ce réseau (source GTFS, site web, identifiant d'agent, voix disponibles) vit dans ce fichier plutôt que dans le code — objectif explicite du projet : dupliquer l'agent sur un autre réseau doit être une opération de paramétrage, pas un nouveau développement. **Point de vigilance : ce fichier contient actuellement une clé API en clair, voir Partie 5.3.** |

### 2.3 Hébergement : pourquoi Clever Cloud

Choix motivé par deux critères explicites du projet, non négociables dès la conception (`CLAUDE.md`) :

- **Hébergement européen.** Clever Cloud est une société française, ses offres standard hébergent en France/UE. Ce n'est pas un choix par défaut : l'alternative envisagée à une étape antérieure (voir `docs/methode-developpement.md`) incluait Scaleway, également français/européen — jamais un hébergeur dont l'origine ou la localisation des données serait inconnue ou hors UE.
- **Simplicité d'exploitation.** Déploiement directement depuis le dépôt Git (déploiement continu), pas de gestion d'infrastructure (conteneurs, orchestration) à la charge de l'équipe — cohérent avec la contrainte du projet de rester maintenable par une équipe non spécialisée en infrastructure.

**[À vérifier — DSI/DPO]** Les conditions contractuelles exactes (accord de sous-traitance RGPD/DPA, garanties de localisation des sauvegardes, durée de rétention des logs d'infrastructure) n'ont pas été vérifiées dans le cadre de ce document — à faire valider formellement avant tout pilote avec de vraies données d'appelants.

### 2.4 Fournisseurs tiers

| Fournisseur | Rôle | Données transmises | Localisation | Statut de vérification |
|---|---|---|---|---|
| **ElevenLabs** | Reconnaissance vocale (ASR), orchestration du modèle de langage, synthèse vocale (TTS), stockage des enregistrements et transcriptions d'appel | Voix de l'appelant, contenu de la conversation (donc tout nom, téléphone, objet perdu énoncé à l'oral), numéro appelant transmis par Twilio | **[À vérifier — DSI/DPO]** | Société non française — localisation précise des serveurs de traitement et de stockage à confirmer via leurs conditions contractuelles avant tout traitement de données réelles. Rétention réglée à 365 jours avec suppression automatique, voir Partie 6.4. |
| **Twilio** | Réception de l'appel entrant et mise en relation avec ElevenLabs ; envoi du SMS récapitulatif d'itinéraire à la demande de l'appelant | Numéro de l'appelant, métadonnées d'appel (durée, horodatage). Pour le SMS : numéro destinataire, et le texte du SMS lui-même, qui peut contenir le prénom/nom de l'appelant et le détail de son itinéraire | **[À vérifier — DSI/DPO]** | Société américaine. L'obtention d'un numéro français a nécessité un dossier de vérification réglementaire propre à la télécom française (« Regulatory Compliance bundle » Twilio — identité, activité) — ce fournisseur n'est pas un simple accès libre, il filtre ses clients en amont. |
| **Google Routes API** | Calcul d'un itinéraire complexe (plusieurs correspondances) en repli, quand le moteur GTFS propre du projet ne trouve rien ; prend en compte une préférence optionnelle (moins de marche / moins de correspondances) | Coordonnées géographiques des deux arrêts, horaire souhaité — aucune donnée identifiant l'appelant | **[À vérifier — DSI/DPO]** | Société américaine. Appel réseau direct depuis notre API (`assistant/outils/itineraire_google.py`), pas via ElevenLabs. |
| **Fournisseur du modèle de langage** (Google — Gemini 3.1 Flash Lite ; testé aussi avec OpenAI — GPT) | Compréhension et génération du dialogue, décision des outils à appeler — à distinguer d'ElevenLabs, qui héberge et connecte ce modèle mais ne « décide » de rien lui-même | Contenu intégral de la conversation, transmis par ElevenLabs (pas d'appel direct depuis notre API) | **[À vérifier — DSI/DPO]** | Sociétés américaines. Le choix du modèle est un paramètre ElevenLabs, pas une intégration directe de notre côté. Modèle retenu après comparaison réelle de plusieurs candidats (deux rejetés pour fabrication de données, le candidat retenu lui-même corrigé sur 5 anomalies distinctes avant d'être jugé fiable — voir Partie 4.4) : critère décisif la fiabilité constatée en appel réel, pas seulement le coût ou la vitesse. Un mécanisme de bascule vers un modèle de secours existe côté ElevenLabs (observé se déclencher au moins une fois) ; son identité précise n'est pas documentée dans nos fichiers — **[À vérifier — DSI]**. |
| **Mecatran** (via la Métropole Mobilité) | Fourniture du flux GTFS statique (horaires, arrêts, lignes) | Aucune donnée personnelle — requête avec clé API en lecture seule | Donnée ouverte (Licence Ouverte 2.0), voir `docs/sources.md` | Clé API actuellement exposée dans le dépôt, voir Partie 5.3. |
| **API Adresse** (data.gouv.fr, gouvernement français) | Géocodage des points de repère (mairies) lors de la préparation des données | Aucune donnée personnelle — adresses publiques des mairies | France, service public | — |
| **GitHub** | Hébergement du code source — pas des données d'appel ni des bases de données, qui vivent exclusivement sur Clever Cloud et ne sont jamais commitées | Code du projet, historique des modifications | **[À vérifier — DSI/DPO]** | Dépôt privé : seuls les comptes explicitement invités y ont accès, pas d'exposition publique par défaut. Le risque réel documenté sur ce projet n'est pas l'accès au dépôt mais le fait qu'un secret collé dedans reste dans l'historique git même après suppression (Partie 1.1, Partie 5.3) — c'est ce risque-là qui justifie la vigilance, pas l'hébergement en lui-même. Sert aussi de dépôt de référence pour `CLAUDE.md` (les règles non négociables du projet) et `docs/spec-assistant-vocal-v0-revisee.md` (le prompt système), tous deux versionnés comme le reste du code. |
| **Clever Cloud** | Exécution de l'application en production (API, back-office) ; déploiement automatique à chaque envoi sur la branche principale du dépôt GitHub (voir Partie 2.3) | Code déployé, variables d'environnement (secrets), bases SQLite de production | France/UE, voir Partie 2.3 | Société française — critère de choix explicite du projet (hébergement européen). |
| **Claude Code** | Outil de développement utilisé pour écrire et faire évoluer le code de ce projet, en dialogue avec l'utilisateur (voir Partie 1.2) | Code source, documentation du projet — jamais de vraies données d'appelant : l'assistant de développement n'est pas exécuté en production et n'a aucun accès aux bases de données en ligne | Anthropic (États-Unis) | **[À vérifier — DSI/DPO]**. Mentionné ici par souci de transparence totale sur tout ce qui a contribué au projet, même un outil qui ne tourne jamais en production. |

---

## Partie 3 — Inventaire des outils exposés à l'agent

Chaque outil est une route HTTP de notre API (`assistant/api/main.py`), appelée par ElevenLabs pendant la conversation selon ce que décide le modèle de langage. Le contrat exact de chaque outil (paramètres, format de réponse) est documenté dans `docs/spec-assistant-vocal-v0-revisee.md`, §4 — ce tableau en donne la vue d'ensemble fonctionnelle et le statut de sécurité/activation.

Les outils sont listés dans l'ordre des sujets voyageur tels qu'ils apparaissent dans le message d'accueil de l'agent (horaires, informations pratiques, itinéraire, objets perdus, sorties) — pas par statut d'activation, pour garder la lisibilité « un outil = un sujet voyageur » plutôt qu'un classement actif/désactivé qui mélangerait les sujets.

| Outil | Rôle | Données personnelles en entrée | Données personnelles en sortie | Statut d'activation |
|---|---|---|---|---|
| `rechercher_arret` | Identifier un arrêt de bus à partir d'un nom dit à l'oral, avec désambiguïsation par commune | Non | Non | Actif par défaut, désactivable (même interrupteur que `horaires_theoriques`) |
| `horaires_theoriques` | Donner les prochains passages théoriques (prévus, pas temps réel) à un arrêt donné | Non | Non | Actif par défaut, désactivable (même interrupteur que `rechercher_arret`) |
| `rechercher_information` | Répondre sur les tarifs, le vélo en libre-service, le transport à la demande, les amendes, à partir d'une base de connaissance indexée | Non | Non | Actif par défaut, désactivable par catégorie (commercial / VLS / TAD / amendes séparément) |
| `calculer_itineraire` | Calculer un trajet théorique (direct ou une correspondance) entre deux arrêts, à partir des seules données GTFS du projet — toujours tenté en premier pour une demande d'itinéraire, avant tout recours à `calculer_itineraire_complexe` (Google Routes), voir Partie 2.1 | Non | Non | **Désactivé par défaut** — activable depuis le back-office, expérimental |
| `rechercher_repere` | Résoudre un lieu dit en clair (« la mairie ») vers l'arrêt le plus proche | Non | Non | **Désactivé par défaut**, même interrupteur que `calculer_itineraire`, expérimental |
| `calculer_itineraire_complexe` | Calculer un trajet plus complexe via Google Routes API, en repli uniquement quand `calculer_itineraire` ne trouve rien ; accepte une préférence optionnelle (moins de marche / moins de correspondances) | Non | Non | **Désactivé par défaut**, interrupteur sur back-office séparé de `calculer_itineraire` — expérimental, dépend d'un appel réseau externe facturé |
| `envoyer_sms_itineraire` | Envoyer par SMS (Twilio) le détail d'un itinéraire déjà présenté à l'oral, à la demande explicite de l'appelant ; recalcule l'itinéraire côté serveur au moment de l'envoi (jamais composé par le modèle de langage, voir Partie 4.4) | **Oui** — prénom/nom (optionnel), numéro de téléphone (obligatoire, confirmé par l'appelant avant envoi) | Non (accusé d'envoi) | **Désactivé par défaut**, interrupteur séparé de `calculer_itineraire_complexe` — dépend d'un envoi réel à un numéro réel, facturé |
| `enregistrer_objet_perdu` | Enregistrer une déclaration d'objet perdu | **Oui** — prénom, nom, numéro de téléphone, email optionnel | Non (accusé d'enregistrement uniquement) | Actif par défaut, désactivable |
| `demander_rappel` | Transmettre une demande de rappel à un conseiller (amende, réclamation, abonnement...) | **Oui** — prénom, nom, numéro de téléphone, email optionnel | Non | Actif, sans interrupteur — porte de sortie systématiquement disponible |
| `transferer_agent` | Signaler qu'un transfert vers un conseiller humain est nécessaire | Non directement (le contexte de la demande peut en contenir) | Non | Actif, sans interrupteur — porte de sortie systématiquement disponible |
| `enregistrer_satisfaction` | Enregistrer si l'appelant juge que l'agent a bien répondu | Non (rattaché à un identifiant de conversation technique, pas à l'identité de l'appelant) | Non | Actif, sans interrupteur |

Deux points d'entrée supplémentaires, non déclenchés par le modèle de langage mais par la plateforme ElevenLabs elle-même :

| Point d'entrée | Rôle | Données personnelles |
|---|---|---|
| `POST /webhooks/elevenlabs/fin_appel` | Reçoit la transcription complète, les métriques d'usage et les métadonnées d'appel en fin de conversation, pour la traçabilité (Partie 7) | **Oui** — transcription intégrale de la conversation, numéro appelant, tout ce qui a été dit à l'oral |
| `POST /webhooks/elevenlabs/personnalisation` | Fournit à ElevenLabs les variables dynamiques de début d'appel (message d'accueil, sujets actifs selon l'activation back-office) | Non |

Chaque route d'outil est protégée par un jeton d'authentification (`Authorization: Bearer ...`, vérifié par `assistant/api/auth.py`) — détail des mécanismes de sécurité en Partie 5.

Toutes les routes `/backoffice/*` (consultation des appels, export CSV, activation des outils, gestion de la prononciation) sont réservées à l'équipe et protégées séparément par une authentification HTTP Basic — elles ne sont jamais appelées par l'agent vocal, uniquement consultées par un humain via un navigateur.

---

## Partie 4 — Code source

### 4.1 Organisation du dépôt

```
assistant/          code applicatif
  ingestion/         chargement GTFS, enrichissement, index phonétique — hors ligne
  outils/            les fonctions exposées à l'agent (Partie 3) + schéma de la base
  api/               FastAPI : routes, validation (schemas.py), authentification (auth.py)
  backoffice/        suivi des appels, exports, activation, back-office web
data/
  gtfs/              GTFS décompressé, non versionné, régénéré à chaque déploiement
  connaissances.md   base de connaissance écrite à la main
  config.yaml        paramètres du réseau (voir Partie 5.3 pour un point de vigilance)
  corpus_index.json  index documentaire + embeddings, versionné (calcul lent, voir Partie 2.2)
  etat/assistant.db  état applicatif persistant — la seule base contenant des données personnelles
docs/                spec, méthode, journal de session, ce dossier d'audit
tests/               scripts de vérification (4.3)
```

Quatre modules à la racine de `assistant/`, en plus de `ingestion/`, `outils/`, `api/`, `backoffice/` :

| Module | Rôle |
|---|---|
| `cherche.py` | Recherche d'arrêt par nom approximatif — combine un code phonétique et une distance d'édition sur le texte, pour absorber les hésitations et déformations de la reconnaissance vocale. |
| `corpus.py` | Rafraîchissement de la base de connaissance : relance l'extraction du site public du réseau et rapporte ce qui a changé (pages modifiées, nouvelles, disparues) sans jamais supprimer une donnée déjà extraite. |
| `demande.py` | Outil de vérification manuelle : rejoue une question et affiche ce que le moteur de recherche documentaire renvoie réellement, avec son score. |
| `evalcorpus.py` | Évaluation automatisée de la qualité de recherche documentaire sur un jeu de questions réelles avec réponse attendue (`tests/questions_evaluation.csv`) — l'instrument de mesure utilisé pour détecter les régressions avant qu'un appelant ne les découvre. |
| `elevenlabs_api.py` | Seuls appels sortants vers l'API ElevenLabs elle-même (pas les webhooks entrants) : changer la voix de l'agent depuis le back-office, sans que l'équipe CRC ait besoin d'un compte ElevenLabs propre. |

### 4.2 Modules critiques, par dossier

« Critiques » regroupe ici des risques de nature différente, à ne pas lire comme un seul et même niveau de gravité : risque de fuite de données personnelles (`backoffice/`, qui manipule les données les plus sensibles), risque de stabilité architecturale (`api/`, point de passage obligé de tout appel externe), risque de coût et de performance (`outils/`, qui interroge les bases et les services tiers). Chaque module ci-dessous est qualifié individuellement plutôt que rangé sous une étiquette unique.

- **`ingestion/`** : pipeline hors ligne, jamais exposé à un appel en direct. Transforme le GTFS brut et le site public en données exploitables par les outils : déduction de la commune de chaque arrêt à partir de ses coordonnées (absente du GTFS source — piège connu, `CLAUDE.md`), gestion des horaires au-delà de minuit (`24:30:00` pour 0h30, autre piège connu), index phonétique pour la reconnaissance des noms d'arrêts.
- **`outils/`** : la logique métier de chaque outil décrit en Partie 3, plus `db.py` qui centralise le schéma SQLite et les migrations. Toutes les requêtes prenant une donnée externe en entrée (nom d'arrêt prononcé, identifiant reçu d'un outil précédent) utilisent des requêtes paramétrées, vérifié explicitement pour la Partie 5.1.
- **`api/`** : point d'entrée unique de tout appel externe. `main.py` déclare les routes, `schemas.py` valide chaque paramètre avant qu'il n'atteigne le code métier (Pydantic), `auth.py` vérifie le jeton ou l'authentification back-office.
- **`backoffice/`** : la seule interface humaine du projet. `appels.py` reçoit et stocke le webhook de fin d'appel (et purge désormais son contenu après 90 jours, Partie 6.4) ; `activation.py` gère l'activation progressive de chaque outil ; `exports.py` produit les exports CSV ; `page.py` génère les pages HTML consultées par l'équipe.

### 4.3 Tests et vérification

Conformément à la règle de méthode « chaque fonction s'accompagne d'un script de vérification » (1.2), le dossier `tests/` contient :

- `verifier_api.py` — vérifie chaque route d'outil contre une API déjà démarrée (authentification, réponse attendue, budget de latence de 300 ms). Couvre les 11 outils exposés à l'agent, y compris les quatre désactivés par défaut (`calculer_itineraire`, `rechercher_repere`, `calculer_itineraire_complexe`, `envoyer_sms_itineraire`) : le script les active le temps du test, puis restaure systématiquement l'état désactivé, y compris en cas d'échec en cours de route.
- `verifier_backoffice.py` — même principe pour les routes du back-office (webhook, exports, activation).
- `verifier_horaires.py` — vérifie les calculs d'horaires contre des cas connus, notamment le piège des heures au-delà de minuit.
- `explorer_gtfs.py` — outil d'exploration manuelle des données GTFS, pour vérifier une hypothèse avant de coder dessus plutôt qu'après.
- `questions_crc.csv` / `questions_evaluation.csv` — jeux de questions réelles avec réponse attendue, utilisés par `evalcorpus.py` pour mesurer la qualité de la recherche documentaire et détecter des régressions.

Ces scripts sont relancés systématiquement avant chaque changement de code touchant l'API ou le back-office. Élargir la couverture de `verifier_api.py` aux outils encore non testés a directement permis de trouver une anomalie de performance réelle avant qu'un appelant ou un audit externe ne la découvre — voir Partie 4.4, entrée du 27/10/2026.

### 4.4 Historique des anomalies trouvées et corrigées

Extrait sélectif du journal complet (`docs/prochaines-etapes.md`), pour donner à l'audit une idée concrète de la discipline de vérification appliquée tout au long du projet — pas une liste exhaustive, qui resterait dans le journal lui-même :

| Date | Anomalie | Comment trouvée | Correction |
|---|---|---|---|
| 02/09/2026 | `rechercher_information` renvoyait une erreur 502 en production | Test réel | Résolu et vérifié le jour même |
| 03/09/2026 | Régression sur le veto lexical du corpus documentaire | Mesure via `evalcorpus` | Détectée avant mise en production, annulée |
| 25/09/2026 | Latence de `calculer_itineraire` doublée par rapport au budget (300 ms) | Mesure directe en local | Cause identifiée (requête coûteuse relancée inutilement) et corrigée le jour même |
| 28/09/2026 | Le prompt citait un exemple de commune (« Marignane ») que le modèle répétait littéralement au lieu de substituer la vraie réponse de l'outil | Lecture d'un vrai transcript d'appel | Exemple reformulé pour être explicitement non littéral |
| 28/09/2026 | Deux candidats LLM testés (Gemini 3.5 Flash-Lite, Qwen3.5-397B-A17B) ont fabriqué des données (nom/téléphone inventés) ou halluciné une contrainte système, en appel réel | Analyse de charges de webhook brutes après appels de test | Aucun des deux déployé ; migration reportée le temps de tester d'autres candidats |
| 29/09/2026 | Gemini 3.1 Flash Lite, retenu ensuite, a montré 5 anomalies distinctes en test réel (dont une fabrication de coordonnées similaire) avant d'être jugé fiable | Même méthode, un appel réel à la fois, un correctif à la fois | Chaque anomalie corrigée et revérifiée le jour même avant de passer à la suivante — voir le détail complet dans le journal |
| 29/09/2026 | Clé API exposée en clair dans des échanges de travail ; base de données propre sans politique de rétention | Relecture volontaire en préparant ce document | Jeton renouvelé et vérifié ; purge automatique à 90 jours implémentée et vérifiée le jour même (Parties 5 et 6) |
| 13/10/2026 | `rechercher_information` répondait en ~10 secondes en production (budget : 300 ms) | Webhook d'un appel réel, latence anormale repérée dans les métriques du tool call | Cause trouvée (modèle d'embeddings chargé à la première requête, plus une vérification réseau superflue de la bibliothèque sous-jacente même avec le modèle déjà en cache) et corrigée le jour même : chargement à vide au démarrage du serveur, hors du chemin critique |
| 13/10/2026 | Le prompt citait un exemple avec les deux communes réelles d'un scénario de test, répété littéralement par le modèle au lieu de la vraie commune dite par l'appelant | Lecture d'un vrai transcript d'appel, après signalement de l'appelant lui-même | Noms de communes de l'exemple remplacés par des valeurs génériques, même principe que l'anomalie du 28/09/2026 sur ce point |
| 13/10/2026 | SMS envoyé sans confirmation effective du numéro ; question de satisfaction validée sans réponse de l'appelant (récidive d'une anomalie déjà vue le 28/09/2026) | Analyse du webhook de deux appels réels successifs | Règles de prompt renforcées pour imposer deux tours de parole distincts (question, puis réponse de l'appelant, puis action) ; la récidive de la question de satisfaction reste partiellement non résolue, probable variabilité du modèle plutôt qu'un défaut de formulation |
| 13/10/2026 | Diagnostic initial erroné : une généralisation de prompt accusée d'avoir causé la récidive ci-dessus | Contradiction relevée par l'utilisatrice, qui ne retrouvait pas le texte en cause dans son prompt ElevenLabs | Vérifié : cette généralisation n'avait en réalité jamais été publiée, donc ne pouvait pas être la cause ; retirée du document de référence, diagnostic corrigé le jour même — gardé ici comme preuve que les diagnostics de ce projet sont systématiquement revérifiés, pas seulement affirmés |
| 27/10/2026 | `rechercher_repere` répondait en ~1,3 s en production (budget : 300 ms) — récidive du même type d'erreur que celle du 25/09/2026 ci-dessus (une requête coûteuse relancée inutilement), déjà corrigée une première fois dans un autre module, mais pas à cet endroit-là du code | Nouveau cas de test ajouté à `verifier_api.py` (Partie 4.3) | Cause confirmée : la requête coûteuse était relancée une fois par résultat candidat (jusqu'à 8 fois pour une seule recherche) au lieu d'une seule fois pour tout l'appel. Corrigée et revérifiée le jour même (1 274 ms → 245 ms) |

Le point commun de ces épisodes : aucune anomalie n'a été découverte par un appelant réel en dehors des tests. Toutes ont été trouvées soit par une vérification automatisée, soit par une relecture attentive d'un appel de test avant toute exposition publique plus large.

---

## Partie 5 — Sécurité

### 5.1 Principes appliqués, vérifiés dans le code au 29/09/2026

- **Authentification par jeton sur chaque route d'outil** (`assistant/api/auth.py`) : comparaison en temps constant (`secrets.compare_digest`), qui protège contre les attaques par mesure de temps de réponse — pas une simple égalité de chaînes.
- **Authentification HTTP Basic séparée sur le back-office** (`verifier_acces_backoffice`), jamais accessible depuis l'agent vocal.
- **Validation stricte de toutes les entrées** via les schémas Pydantic de FastAPI (`assistant/api/schemas.py`) : avant qu'une donnée reçue d'un outil n'atteigne le code métier, elle est vérifiée automatiquement (bon format, bonne longueur, type attendu) — un modèle de langage ne peut pas envoyer n'importe quoi à notre base de données. Preuve concrète et datée de son utilité : le 28/09/2026, un modèle de langage testé (Gemini 3.1 Flash Lite) a tenté d'appeler `enregistrer_objet_perdu` avec `nom="Inconnu"` et `telephone="0000000000"` plutôt que de poser la question à l'appelant — bloqué le jour même par une contrainte ajoutée sur ces deux champs (longueur minimale, puis forme d'un numéro français valide).
- **Requêtes SQL exclusivement paramétrées.** Vérification explicite menée pour ce document : les trois seuls endroits du code utilisant une interpolation de chaîne dans une requête SQL (`assistant/outils/db.py`, `assistant/backoffice/exports.py`) construisent leur requête à partir de noms de table/colonne codés en dur dans le code (listes Python fixes), jamais à partir d'une donnée reçue d'un appelant ou d'un outil. Partout ailleurs (45 requêtes au total), les valeurs variables ne sont jamais collées directement dans le texte de la requête : elles passent par un emplacement réservé — le caractère `?` — que la base de données remplit elle-même de façon sécurisée, la protection standard contre l'injection SQL.
- **Paramétrage externalisé** : tout ce qui est propre au réseau (source GTFS, identifiant d'agent, voix disponibles) vit dans `data/config.yaml` et des variables d'environnement, jamais codé en dur — à une exception près, voir 5.3. Les variables d'environnement sont saisies manuellement dans l'interface de configuration de Clever Cloud (jamais écrites dans un fichier du dépôt).

### 5.2 Surface exposée

Voir Partie 3 pour le détail. En résumé : 11 routes d'outils + 2 routes de webhook accessibles publiquement (protégées par jeton), routes `/backoffice/*` accessibles publiquement mais protégées par mot de passe (jamais appelées par l'agent). Aucune base de données n'est exposée directement — les fichiers SQLite ne sont accessibles que depuis le code serveur.

**[À vérifier — DSI]** Points non contrôlés dans le cadre de ce document :
- Aucune limitation de débit (*rate limiting*) constatée dans le code : un client qui connaîtrait le jeton pourrait appeler les routes sans restriction de fréquence. Risque faible tant que le jeton reste confidentiel, mais absent comme deuxième ligne de défense.
- Chiffrement en transit (HTTPS) : Clever Cloud fournit un certificat TLS par défaut sur les domaines `*.cleverapps.io`, mais la configuration exacte (versions TLS acceptées, HSTS) n'a pas été vérifiée pour ce document.

### 5.3 Gestion des secrets

Deux catégories de secrets coexistent dans ce projet, à ne pas confondre :

- **Secrets délivrés par un fournisseur** (`ELEVENLABS_API_KEY`, la clé Mecatran du flux GTFS, `GOOGLE_ROUTES_API_KEY`, `TWILIO_ACCOUNT_SID`/`TWILIO_AUTH_TOKEN`) : générés et reconnus par le système du fournisseur, à renouveler depuis leur propre interface.
- **`API_TOKEN`** : un secret inventé par le projet lui-même, comparé tel quel par notre propre code (`assistant/api/auth.py`). Sert de mot de passe pour les 11 outils et de jeton d'URL pour le webhook de fin d'appel — deux usages qui l'exposent par nature à des endroits semi-publics (en-têtes de configuration ElevenLabs, URL visible dans des captures d'écran).
- **`BACKOFFICE_MOT_DE_PASSE`** : corrigé le 29/09/2026, un secret séparé pour l'accès au back-office (identifiant/mot de passe HTTP Basic), choisi librement par l'utilisateur et indépendant d'`API_TOKEN`. Avant cette date, le même jeton servait aux deux usages — compromettre `API_TOKEN` (plus exposé par construction) aurait donné accès aux journaux d'appels du back-office, dont jusqu'à 90 jours de transcripts (Partie 6.4).

`.env` (qui contient ces deux secrets en local) est bien exclu du dépôt (`.gitignore`), vérifié.

**Incidents d'exposition en clair, quatre occurrences entre le 28/09 et le 12/10/2026, toutes corrigées le jour même** : `API_TOKEN` a circulé en clair dans des charges de webhook collées dans des échanges de travail (28/09, 09/10, 12/10) ; `GOOGLE_ROUTES_API_KEY` de la même façon dans une commande de test (08/10). Même réflexe appliqué à chaque fois : jeton considéré compromis par principe, rotation complète aux endroits qui en dépendent (variable d'environnement Clever Cloud, en-têtes ElevenLabs, URL du webhook de fin d'appel), vérifiée sur un appel réel avant de considérer l'incident clos. **Aucun de ces secrets n'est exposé à ce jour.** Cause récurrente identifiée : coller une commande ou une charge complète sans la nettoyer au préalable, pas un défaut du mécanisme de secret lui-même — voir recommandation 5 ci-dessous.

**Point encore ouvert** : `data/config.yaml` est versionné par git (absent du `.gitignore`, malgré ce qu'affirme `CLAUDE.md`) et contient la clé API Mecatran du flux GTFS en clair, présente dans l'historique depuis plusieurs commits. C'est une clé que notre propre code utilise pour interroger Mecatran, pas une donnée qui nous est transmise par un système tiers — et le risque concret est faible : en lecture seule, elle ne donne accès qu'à un flux de données déjà public en Licence Ouverte, rien de plus qu'un appelant ne pourrait trouver autrement. Mais sa présence en clair contredit la propre règle de sécurité du projet, et la corriger est rapide — à régénérer par hygiène avant l'audit, `data/config.yaml` à ajouter au `.gitignore`, et `CLAUDE.md` à corriger sur ce point.

**Piste d'amélioration identifiée en re-créant le webhook de fin d'appel** : le formulaire ElevenLabs propose une syntaxe `{{ variable d'environnement }}` pour l'URL des webhooks, réservée à la plateforme Agents. Actuellement, le jeton apparaît en clair dans l'URL elle-même, donc visible dans toute capture d'écran ou export de configuration — passer par cette syntaxe éviterait cette exposition. Non fait à ce jour — configuration à faire côté ElevenLabs (variable à déclarer, URL du webhook à republier), voir recommandation 1 ci-dessous.

### 5.4 Limites connues

- **Séparation des secrets par usage : corrigée le 29/09/2026.** Un seul secret (`API_TOKEN`) servait auparavant à la fois aux outils, au webhook, et au mot de passe back-office — compromettre le plus exposé des trois (`API_TOKEN`) donnait accès aux journaux d'appels. `BACKOFFICE_MOT_DE_PASSE` est désormais indépendant (5.3).
- **Rotation entièrement manuelle**, répartie sur deux plateformes externes (Clever Cloud, ElevenLabs) sans mécanisme de transition — la rotation du 28/09 a provoqué une courte interruption de service (un webhook modifié mais non publié côté ElevenLabs), révélatrice de cette fragilité opérationnelle. Trois expositions supplémentaires du même type entre le 08 et le 12/10/2026 (Partie 5.3) confirment que ce n'est pas un risque isolé : la cause (coller une commande ou une charge de diagnostic sans la nettoyer) se répète facilement tant qu'aucune consigne systématique n'est actée.
- **Pas de vérification de signature HMAC** sur le webhook de fin d'appel — la sécurité repose entièrement sur le secret dans l'URL, alors qu'ElevenLabs propose HMAC nativement (secret déjà généré côté ElevenLabs, non exploité côté code).
- **Politique de rétention sur notre propre base de données : partiellement corrigée.** `appels.donnees_brutes` est purgé automatiquement après 90 jours depuis le 29/09/2026 (Partie 6.4). `objets_perdus`/`demandes_rappel` restent, eux, sans politique de rétention — décision produit encore à trancher, pas seulement technique.

### 5.5 Recommandations avant un pilote public plus large

1. Mettre en place la vérification de signature HMAC du webhook de fin d'appel, et au passage faire transiter `API_TOKEN` par la syntaxe `{{ variable d'environnement }}` d'ElevenLabs plutôt qu'en clair dans l'URL (5.3) — deux actions techniques concrètes côté ElevenLabs, pas encore faites, probablement à mener manuellement.
2. Régénérer la clé Mecatran et corriger `.gitignore`/`CLAUDE.md` — ceci ne change rien à l'usage de GitHub pour héberger le code : seul le secret doit en sortir, pas le dépôt lui-même.
3. Trancher et implémenter une durée de rétention pour `objets_perdus`/`demandes_rappel` et `sms_envoyes` (Partie 6.4) — `appels` déjà fait.
4. Envisager une limitation de débit basique si le périmètre d'appel s'élargit.
5. Acter formellement une consigne de manipulation des secrets en ligne de commande (saisie via `read -s` systématique, jamais en clair dans une commande affichée ni dans une charge de diagnostic partagée sans l'avoir expurgée) — quatre incidents du même type en deux semaines (5.3) suggèrent que ça ne se résoudra pas seul.
6. Concevoir et développer un dispositif pour les demandes d'accès/rectification/effacement RGPD d'un appelant (recherche par numéro de téléphone, export, suppression groupée) — voir Partie 6.6, rien n'existe à ce jour.

---

## Partie 6 — RGPD et données personnelles

### 6.1 Données personnelles collectées

| Fonctionnalité | Données | Table / emplacement |
|---|---|---|
| Déclaration d'objet perdu | Prénom, nom, téléphone, email (optionnel) | `objets_perdus` (base `data/etat/assistant.db`) |
| Demande de rappel | Téléphone, prénom/nom (optionnel), email (optionnel), motif, résumé de la demande | `demandes_rappel` (même base) |
| **Chaque appel, sans exception** | **Transcript intégral de la conversation (donc tout nom, téléphone, description d'objet énoncé à l'oral, même sans déclaration formelle si l'appelant en a fait mention), numéro de l'appelant, identifiants d'appel** | `appels.donnees_brutes` (même base) — charge JSON complète reçue d'ElevenLabs, stockée telle quelle |
| Envoi du SMS d'itinéraire | Numéro de téléphone (obligatoire), prénom/nom (optionnel) — repris dans le texte du SMS effectivement envoyé, conservé tel quel pour pouvoir vérifier après coup ce que l'appelant a reçu | `sms_envoyes` (même base) |
| Côté ElevenLabs (hors de notre infrastructure) | Audio de l'appel, transcript, mêmes métadonnées | Infrastructure ElevenLabs — rétention désormais réglée à 365 jours avec suppression automatique (28/09/2026) |

### 6.2 Finalités

- `objets_perdus` / `demandes_rappel` : traiter la demande concrète de l'appelant (retrouver un objet, être rappelé par un conseiller).
- `sms_envoyes` : transmettre à l'appelant, par un canal qu'il a choisi lui-même, le détail d'un itinéraire déjà annoncé à l'oral — pas de finalité au-delà de ce service ponctuel.
- `appels.donnees_brutes` : traçabilité économique et environnementale du projet (coût, tokens, minutes voix — exigence explicite de `CLAUDE.md`), suivi qualité, débogage.

**Point de vigilance (minimisation des données)** : la finalité de traçabilité ne nécessite que des métriques (coût, durée, modèle utilisé) — déjà extraites dans des colonnes dédiées de la table `appels`. Le fait de conserver *en plus* la charge JSON brute intégrale, transcript inclus, va au-delà de cette finalité. C'est un choix de conception compréhensible (déboguer un comportement d'agent nécessite de revoir la conversation complète, comme on l'a fait à de nombreuses reprises pendant ce projet), mais qui doit être assumé explicitement et borné dans le temps plutôt que subi par défaut.

### 6.3 Base légale — **[À qualifier — DPO]**

La qualification formelle revient au DPO ; ce qui suit est la lecture de travail du projet, pour lui donner un point de départ plutôt qu'une page blanche.

**Déclarations d'objet perdu et demandes de rappel.** Dans les deux cas, c'est l'appelant lui-même qui sollicite une action concrète (retrouver son bien, être recontacté) en communiquant volontairement ses coordonnées dans ce but précis. La base la plus probable est l'exécution d'une démarche demandée par la personne elle-même, assimilable à l'exécution d'une mesure précontractuelle ou d'un service rendu à sa demande — pas un traitement que le réseau déciderait de sa propre initiative. Point à trancher par le DPO : s'agit-il juridiquement d'un contrat de transport, d'une mission de service public, ou d'un autre fondement propre à l'exploitant du réseau ?

**Consentement marketing (`opt_in_marketing`).** Seul traitement du projet reposant explicitement sur le consentement : la question n'est posée qu'une fois, après l'enregistrement d'une déclaration ou d'une demande, jamais reproposée en cas de refus (voir `docs/spec-assistant-vocal-v0-revisee.md`, section Opt-in marketing). C'est la forme de consentement la plus facile à défendre (libre, spécifique, non réitéré de force), mais son articulation avec les autres traitements (transcript, traçabilité) reste à documenter : le refus du marketing n'a par exemple aucun effet sur la conservation du transcript de l'appel, qui obéit à une autre logique.

**Transcript intégral de chaque appel (`appels.donnees_brutes`).** C'est le point le plus délicat, parce que sa base légale n'est pas la même que celle des déclarations : l'appelant ne « demande » pas que sa conversation soit intégralement conservée, c'est une conséquence du choix d'architecture du projet (ElevenLabs renvoie la charge complète, pas seulement un résumé). Deux pistes possibles, à trancher par le DPO : l'intérêt légitime du responsable de traitement (suivi qualité, débogage, obligation de traçabilité économique posée par `CLAUDE.md`), à mettre en balance avec l'attente raisonnable de l'appelant qui n'a pas explicitement consenti à cette conservation détaillée ; ou une qualification différente si le réseau considère ce traitement comme nécessaire à l'exécution du service rendu. Dans les deux cas, la durée de rétention (90 jours, Partie 6.4) et la minimisation déjà engagée (Partie 6.2) sont des éléments qui pèsent en faveur du projet, mais ne remplacent pas la qualification elle-même.

### 6.4 Durées de conservation

- **ElevenLabs : corrigé le 28/09/2026.** Rétention 365 jours, suppression automatique de la transcription/PII et de l'audio après ce délai, appliquée aux conversations existantes. Vérifié sur un appel réel (`deletion_time_unix_secs` renseigné, `delete_transcript_and_pii: true`, `delete_audio: true`).
- **`appels.donnees_brutes` : corrigé le 29/09/2026.** Purge automatique (transcript intégral, numéro de l'appelant) après 90 jours, sans supprimer la ligne ni les métriques déjà extraites (`duree_secs`, `cout_usd`, `minutes_asr`/`tts`, `modeles_llm`, `tokens_llm`...), qui restent disponibles indéfiniment comme l'exige `CLAUDE.md`. Purge exécutée au démarrage de l'application puis une fois par jour tant qu'elle tourne (`assistant/backoffice/appels.py`, `purger_transcripts_expires`). Vérifié en local : un appel de 100 jours voit son contenu vidé, un appel récent reste intact, et un recalcul des métriques après purge (`retraiter_tracabilite`) ne les écrase pas — garde-fou ajouté à cette occasion. Durée de 90 jours choisie comme compromis entre le besoin de suivi qualité de l'équipe (relecture d'un appel récent) et la minimisation des données.
- **`objets_perdus` / `demandes_rappel` : encore ouvert.** Une fonction de suppression existe (`supprimer_objet_perdu`) mais reste un geste manuel, prévue à l'origine pour nettoyer des données de test, pas comme mécanisme de conformité systématique. Contrairement au transcript d'appel, ces données restent activement utiles tant que la demande n'est pas résolue (objet retrouvé, rappel effectué) — la durée de rétention appropriée dépend donc d'une décision produit (combien de temps une recherche d'objet perdu reste active ?) plutôt que d'un choix purement technique. **Reste à trancher avec l'utilisateur avant l'audit.**
- **`sms_envoyes` : encore ouvert, pas encore traité.** Aucune fonction de suppression ni de purge automatique n'existe à ce jour pour cette table — même situation que `objets_perdus`/`demandes_rappel` ci-dessus, à trancher avec la même décision produit (le texte conservé contient potentiellement nom et numéro de l'appelant).

### 6.5 Sous-traitants et transferts hors UE

Voir Partie 2.4 pour le détail par fournisseur. Synthèse : ElevenLabs, Twilio et le fournisseur du modèle de langage (Google ou OpenAI selon le modèle retenu) sont des sociétés non européennes dont la localisation exacte de traitement n'a pas été vérifiée contractuellement — **[À vérifier — DSI/DPO]** avant tout traitement de données réelles d'appelants publics.

Le numéro de téléphone de l'appelant transite nécessairement par l'infrastructure Twilio dès qu'un SMS est envoyé : Twilio n'est pas un simple tuyau transparent, c'est un service avec sa propre API et sa propre console de journaux. Twilio a donc très probablement sa propre politique de rétention sur ce numéro et sur le contenu du SMS, indépendante de notre table `sms_envoyes` (Partie 6.4) — **[À vérifier — DSI/DPO]**.

Point distinct, vérifié dans le code : **aucune route n'est configurée pour recevoir une réponse SMS d'un appelant.** Si quelqu'un répond au SMS reçu, cette réponse arrive côté Twilio mais n'est traitée par aucun mécanisme de notre projet — ni transmise, ni visible dans le back-office. Le comportement par défaut de Twilio dans ce cas n'a pas non plus été vérifié — **[À vérifier]**, à documenter ou à corriger, ne serait-ce que pour s'assurer qu'une réponse n'est pas silencieusement perdue si elle contenait, par exemple, une demande de ne plus recevoir de SMS.

### 6.6 Droits des personnes

Conformément au RGPD, tout appelant doit pouvoir demander l'accès, la rectification ou l'effacement des données le concernant. **[À formaliser — DSI/DPO]** Aucun mécanisme self-service n'existe aujourd'hui pour exercer ce droit : si un voyageur nous contacte à cette fin, la demande serait traitée par une intervention manuelle en base de données par l'équipe technique — un processus encore à documenter formellement (délai de réponse, canal de demande) avant l'ouverture d'un pilote public.

**Dispositif envisagé, pas encore développé**, pour qu'un agent humain puisse traiter une telle demande rapidement — probablement rare, mais sans jamais lui faire perdre de temps : une recherche par numéro de téléphone dans le back-office, qui retournerait tous les enregistrements liés à ce numéro (appels, objets perdus, demandes de rappel, SMS), avec un export prêt à joindre à une réponse (PDF ou CSV) et une suppression groupée pour le droit à l'effacement. Aucune de ces trois briques n'existe dans le code à ce jour — un vrai développement, pas une simple documentation, mis en recommandation (Partie 5.5).

### 6.7 Mesures de sécurité des données personnelles

Voir Partie 5 pour le détail complet (authentification, validation des entrées, requêtes paramétrées). Aucune mesure spécifique de chiffrement au repos des données personnelles dans la base SQLite au-delà de ce que fournit Clever Cloud par défaut — **[À vérifier — DSI]**.

### 6.8 Éléments pour l'analyse d'impact (AIPD)

Ce document fournit la matière première ; l'analyse elle-même reste à mener par le DPO. Points qu'elle devra couvrir en priorité, par ordre d'importance selon ce qui a été trouvé en préparant ce dossier :
1. Valider la durée de rétention retenue pour `appels.donnees_brutes` (90 jours, corrigé le 29/09/2026 — Partie 6.4) et trancher celle de `objets_perdus`/`demandes_rappel` et de `sms_envoyes`, toutes deux encore ouvertes.
2. La qualification de la base légale pour chaque table (6.3).
3. Les transferts hors UE vers ElevenLabs, Twilio et le fournisseur de modèle de langage (6.5) — Twilio traite désormais aussi le contenu du SMS d'itinéraire, pas seulement les métadonnées d'appel (Partie 2.4).
4. La formalisation des droits des personnes (6.6).

---

## Partie 7 — Traçabilité et gouvernance

### 7.1 Traçabilité économique et environnementale

Exigence non négociable du projet, telle que formulée dans `CLAUDE.md` :

> Chaque appel logge le modèle utilisé, les tokens consommés, les minutes de reconnaissance et de synthèse vocale, et le coût estimé. Ces données servent à l'évaluation économique et environnementale du projet, elles ne sont pas reconstituables après coup.

Concrètement, huit colonnes dédiées sur la table `appels` (`assistant/backoffice/appels.py`, `_extraire_tracabilite`), extraites automatiquement de chaque webhook de fin d'appel : durée, coût réel (pas estimé — la valeur facturée par ElevenLabs), minutes de reconnaissance et de synthèse vocale séparément, détail des modèles de langage utilisés (utile quand un appel bascule sur un modèle de secours, voir 4.4), tokens consommés, outils réellement appelés, voix utilisées. Ces colonnes ne contiennent aucune donnée personnelle et ne sont jamais concernées par la purge de 90 jours (Partie 6.4) — c'est précisément ce qui permet de purger le reste sans violer l'exigence de traçabilité ci-dessus.

Une fonction de secours, `retraiter_tracabilite`, permet de recalculer ces colonnes depuis `donnees_brutes` si la logique d'extraction est corrigée après coup (par exemple si un nouveau type d'appel a un format légèrement différent, déjà arrivé une fois). Elle ne fonctionne que sur les appels dont `donnees_brutes` n'a pas encore été purgé — une fenêtre de 90 jours pour corriger une erreur d'extraction, au-delà les métriques déjà calculées restent figées.

`resumer_tracabilite` agrège ces données pour le tableau de bord du back-office (durée moyenne, coût total, répartition des outils utilisés, répartition des appels par tranche de 15 minutes, décompte des SMS envoyés) — l'outil de pilotage économique du projet au jour le jour.

**Deux mécanismes de retour distincts, à ne pas confondre :**
- **Satisfaction déclarée par l'appelant** (`satisfaction_appels`, outil `enregistrer_satisfaction`) : une réponse oui/non par conversation, posée une seule fois en fin d'appel, jamais avant que l'appelant ait explicitement répondu (correction du 28/09/2026, Partie 4.4).
- **Évaluation de l'équipe** (`evaluations_appels`, back-office) : un humain relit un appel et le juge « bonne » ou « mauvaise » réponse, avec une note libre optionnelle directement dans l'outil de back-office. Plusieurs évaluations possibles par appel, jamais d'écrasement d'un avis précédent — l'historique complet reste consultable.

### 7.2 Activation progressive des outils

Chaque outil (Partie 3) peut être coupé indépendamment depuis le back-office, plus un interrupteur général (`activation_outils`, clé `"tous"`) qui coupe tout d'un coup si nécessaire. Trois raffinements notables :

- **`calculer_itineraire`/`rechercher_repere` démarrent désactivés par défaut** (`_OUTILS_INACTIFS_PAR_DEFAUT`, `assistant/outils/db.py`) — la fonctionnalité expérimentale d'itinéraire ne s'active jamais automatiquement à un nouveau déploiement, elle doit être explicitement rallumée. Même principe pour `calculer_itineraire_complexe` et `envoyer_sms_itineraire`, chacun avec son propre interrupteur, volontairement indépendant des autres : dépendent tous deux d'un appel réseau externe facturé (Google Routes, Twilio), un niveau de confiance encore distinct du reste des outils.
- **`rechercher_information` s'active par catégorie** (commercial, vélo en libre-service, transport à la demande, amendes) plutôt que d'un bloc — aligné sur la grille de classification réelle utilisée par l'équipe CRC, pas sur un découpage technique arbitraire. Un réseau peut par exemple couper le vélo en libre-service sans couper les tarifs.
- **Un outil désactivé renvoie une erreur HTTP 503**, pas une réponse habillée en « rien trouvé ». Choix délibéré, vérifié en conditions réelles avant d'être retenu : à chaque fois qu'un outil a échoué techniquement en test (404, 422...), l'agent vocal a basculé proprement vers la sortie (transfert ou rappel) sans jamais inventer de réponse — plutôt que de fabriquer une réponse « vide » différente pour chacun des contrats de sortie possibles, au risque de s'y contredire, le projet réutilise ce comportement déjà éprouvé.

Conséquence directe pour la confiance de l'appelant : le message d'accueil de l'agent ne promet jamais une capacité coupée. La variable dynamique `outils_actifs` (webhook de personnalisation, Partie 2.1) est recalculée à chaque appel à partir de l'état réel de l'activation back-office — si un outil est coupé, il disparaît du message d'accueil, pas seulement du comportement.

### 7.3 Méthode de test et d'amélioration continue

Deux boucles de mesure distinctes, toutes deux documentées dans le dépôt avant même d'être utilisées :

**Mesure automatisée de la recherche documentaire** (`assistant/evalcorpus.py`) : un jeu de questions réelles avec la bonne réponse attendue (`tests/questions_evaluation.csv`) donne un taux de réussite chiffré, comparable dans le temps — l'instrument qui a permis de détecter une régression avant mise en production (4.4) plutôt que de la découvrir par un appelant.

**Remontée des vrais besoins par l'équipe CRC** (`docs/methode-amelioration-continue.md`) : l'équipe CRC répond déjà au téléphone aujourd'hui, en parallèle de ce projet. Pour chaque vraie question posée par un appelant (sur n'importe quel canal, pas seulement l'assistant), un membre de l'équipe note une ligne reformulée à la main — par exemple « comment recharger ma carte » — jamais le nom de la personne ni un enregistrement. Ces lignes servent ensuite de jeu de questions réelles pour tester si l'assistant sait y répondre, avec le même instrument de mesure que la mesure automatisée ci-dessus (`evalcorpus`). Chaque échec se classe dans une grille à trois catégories qui structure la correction : trou de vocabulaire (la réponse existe dans la base de connaissance, mais sous un autre nom), trou de contenu (la réponse n'existe nulle part), ou vraie question hors périmètre (la bonne réponse est un transfert humain, pas une page à ajouter). Le point RGPD : comme c'est un humain qui reformule à la main, sans jamais copier de donnée personnelle, ce mécanisme n'a pas besoin d'une analyse d'impact ni de l'accord du DPO — contrairement au reste du système, qui manipule des transcripts bruts (Partie 6).

**Test en appel réel avant toute décision structurante** : au-delà de ces deux boucles, chaque changement de modèle de langage candidat a été validé par des appels réels sur des scénarios ciblés, avec analyse systématique de la charge JSON brute du webhook (pas seulement de ce qui s'est entendu à l'oral) — c'est cette méthode qui a permis de disqualifier deux candidats sur des fabrications de données invisibles à l'écoute d'un appel normal, et de trouver puis corriger cinq anomalies distinctes sur le candidat finalement retenu, le jour même de chaque découverte (4.4). Aucune bascule en production sans ce passage par un test réel.

---

## Partie 8 — Perspective : vers un déploiement public sécurisé

Cette partie se distingue volontairement du reste du document : les Parties 1 à 7 documentent l'existant, celle-ci pose une question ouverte plutôt que d'y répondre — ce document reste un audit, pas une feuille de route stratégique, et ce choix n'est pas anodin : la DSI doit se prononcer sur des faits vérifiés, pas sur une recommandation d'orientation qui ne lui appartient pas de recevoir toute faite.

Plusieurs limites documentées dans ce dossier (rotation manuelle des secrets, Partie 5.3-5.4 ; sous-traitants hors UE non vérifiés contractuellement, Partie 6.5 ; absence de dispositif RGPD en self-service, Partie 6.6) sont compatibles avec un POC testé par une équipe réduite, mais se poseraient différemment à l'échelle d'un vrai public. La question que ce document soumet à la DSI, sans y répondre à sa place : la suite envisageable est-elle d'industrialiser cette architecture telle quelle avec les correctifs recommandés (Partie 5.5), ou de la faire évoluer vers des environnements mieux maîtrisés et sécurisés par les équipes infrastructure du groupe (à titre d'exemple de piste, un hébergement opéré par Transdev) — en conservant l'essentiel des choix fonctionnels et techniques déjà faits et documentés ici, sans repartir d'une page blanche ?

---

*Suite prévue : annexes (glossaire, références officielles, extraits de code complets, schémas).*
