# Dossier d'audit DSI — Assistant vocal, zone Étang

Document en construction, chapitre par chapitre, pour l'audit interne DSI précédant un pilote public sur une filiale. Structure complète et méthode de rédaction actées avec l'utilisateur le 29/09/2026 (voir `docs/prochaines-etapes.md`).

Chaque affirmation de ce document vient d'un fichier réel du dépôt, du code lui-même, ou d'une vérification technique directe. Quand un fait ne peut pas être vérifié depuis le dépôt seul (contrats fournisseurs, localisation exacte de serveurs tiers...), il est marqué **[À vérifier — DSI/DPO]** plutôt qu'affirmé.

Statut : parties 1 à 7 rédigées. Annexes à venir.

---

## Partie 1 — Intention et genèse

### 1.1 Résumé exécutif

Reprise textuelle du contexte tel que défini dans `CLAUDE.md`, le document de référence du projet :

> Démonstrateur d'assistant téléphonique pour un réseau de bus de la zone Étang de Berre. Il répond aux appels de voyageurs sur les tarifs, les horaires théoriques et les déclarations d'objets perdus. Il n'est branché à aucun système métier : les données viennent de l'open data et d'une base de connaissance écrite à la main.

Ce dernier point est structurant pour l'audit : l'assistant ne lit ni n'écrit dans aucun système d'information existant (billettique, CRM, planification) — son seul état propre est la petite base SQLite décrite en Partie 2, et ses seules sources externes sont des données ouvertes (GTFS, site public du réseau).

### 1.2 Genèse et méthode de conception

Ce projet a été construit par l'utilisateur lui-même, non-développeur de profession, avec Claude Code comme assistant de développement — un choix assumé et documenté dès l'origine (`docs/methode-developpement.md`), pas découvert a posteriori. La méthode retenue, écrite avant la première ligne de code, repose sur des règles de travail explicites :

- **Une session de travail = un objectif** — jamais une demande ouverte du type « construis l'application ».
- **Un commit à chaque état qui fonctionne**, pour toujours pouvoir revenir en arrière.
- **« N'accepte jamais du code que tu ne peux pas résumer en une phrase »** — condition explicite pour que l'utilisateur reste en mesure de maintenir seul ce qui est écrit pour lui, une fois le projet livré.
- **Chaque fonction s'accompagne d'un script de vérification** — pas de confiance aveugle dans le code produit, une vérification systématique.
- **Déployer tôt** — une API en ligne dès l'étape 3 de la méthode, avant même que les fonctionnalités ne soient complètes, pour rencontrer les problèmes d'infrastructure quand il n'y a encore rien à perdre.

Fait notable pour ce document : la méthode originelle contenait déjà, avant tout développement, l'avertissement suivant sur la gestion des secrets — *« Une clé d'API poussée sur GitHub reste dans l'historique même après suppression »*. La vigilance était donc présente dès la conception ; elle a néanmoins été prise en défaut une fois en cours de route (la clé Mecatran de `data/config.yaml`, Partie 5.3), trouvée et en cours de correction au moment de cet audit — signe que la méthode fonctionne (le problème a été détecté par une relecture volontaire, pas par un incident), pas qu'elle a échoué.

Le développement s'est déroulé par itérations courtes et vérifiées, documentées au fil de l'eau dans `docs/prochaines-etapes.md` (le journal de bord complet du projet, plusieurs centaines d'entrées datées) — la Partie 4.4 de ce document en reprend les épisodes les plus significatifs pour l'audit.

### 1.3 Périmètre fonctionnel actuel

L'assistant répond aujourd'hui sur six familles de sujets, chacune correspondant à un ou plusieurs outils détaillés en Partie 3 :

1. **Horaires théoriques** — prochains passages ou créneau horaire à un arrêt donné.
2. **Informations commerciales et pratiques** — tarifs, abonnements, vélo en libre-service, transport à la demande, amendes, à partir d'une base de connaissance indexée depuis le site public du réseau.
3. **Objets perdus** — déclaration complète (nature, description, ligne, date, lieu, coordonnées).
4. **Demande de rappel** — vers un conseiller humain, pour tout sujet hors périmètre automatisable.
5. **Itinéraire** — trajet théorique direct ou avec une correspondance, **fonctionnalité expérimentale désactivée par défaut**.
6. **Sortie vers un humain** — transfert ou rappel systématique dès que l'assistant ne sait pas répondre, jamais d'invention.

Aucun horaire ou tarif temps réel : tout est présenté comme prévu, jamais comme garanti — choix assumé dans le prompt de l'agent, cohérent avec l'absence de connexion à un système métier (1.1).

### 1.4 État d'avancement

Le projet a passé son test interne (démonstration à l'équipe CRC) et pourrait devenir, sous réserve de cet audit, un pilote public sur une filiale du groupe — un test grandeur réelle, mais toujours sans développement lourd supplémentaire. C'est le contexte précis de ce document : documenter exhaustivement l'existant pour que la DSI puisse se prononcer en connaissance de cause, plutôt que de laisser le POC continuer à vivre sans traçabilité formelle de ses choix.

### 1.5 Ce que ce document couvre

Architecture et choix techniques (Partie 2), inventaire complet des outils exposés à l'agent (Partie 3), organisation et anomalies connues du code (Partie 4), sécurité (Partie 5), RGPD et données personnelles (Partie 6), traçabilité et gouvernance (Partie 7 — à venir). Il ne couvre pas les aspects contractuels et organisationnels qui ne se lisent pas dans le dépôt de code (accords de sous-traitance RGPD, conditions contractuelles des fournisseurs) — signalés partout où c'est pertinent comme **[À vérifier — DSI/DPO]**.

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
| Recherche floue (noms d'arrêts) | [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) | 3.14+ | Correspondance phonétique/orthographique tolérante aux hésitations et déformations de la reconnaissance vocale (« Émile Ripert » entendu correctement malgré une prononciation approximative). Bibliothèque locale, aucun appel réseau. |
| Indexation documentaire | [fastembed](https://github.com/qdrant/fastembed) | 0.8+ | Calcule des embeddings pour la recherche dans la base de connaissance (tarifs, FAQ). Modèle exécuté localement, pas d'appel à une API d'embeddings tierce — le résultat est un fichier JSON versionné (`data/corpus_index.json`), pas une base vectorielle à part entière (explicitement écarté par les règles du projet, jugée disproportionnée à cette échelle). |
| Extraction de contenu web | BeautifulSoup4, markdownify | — | Transforment les pages du site public du réseau en base de connaissance exploitable (étape d'ingestion, hors ligne, pas exposée à l'agent en direct). |
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
| **ElevenLabs** | Reconnaissance vocale (ASR), orchestration du modèle de langage, synthèse vocale (TTS), stockage des enregistrements et transcriptions d'appel | Voix de l'appelant, contenu de la conversation (donc tout nom, téléphone, objet perdu énoncé à l'oral), numéro appelant transmis par Twilio | **[À vérifier — DSI/DPO]** | Société non française — localisation précise des serveurs de traitement et de stockage à confirmer via leurs conditions contractuelles avant tout traitement de données réelles. Réglages de rétention actuellement non configurés, voir Partie 6.4. |
| **Twilio** | Opérateur téléphonique : réception de l'appel entrant, mise en relation avec ElevenLabs | Numéro de l'appelant, métadonnées d'appel (durée, horodatage) | **[À vérifier — DSI/DPO]** | Société américaine. |
| **Fournisseur du modèle de langage** (Google — Gemini ; testé aussi avec OpenAI — GPT) | Compréhension et génération du dialogue, décision des outils à appeler | Contenu intégral de la conversation, transmis par ElevenLabs (pas d'appel direct depuis notre API) | **[À vérifier — DSI/DPO]** | Sociétés américaines. Le choix du modèle est un paramètre ElevenLabs, pas une intégration directe de notre côté — voir `docs/prochaines-etapes.md` pour la méthode de sélection et les critères de fiabilité appliqués (comparaison de plusieurs modèles sur des cas réels avant tout changement en production). |
| **Mecatran** (via la Métropole Mobilité) | Fournit le flux GTFS statique (horaires, arrêts, lignes) | Aucune donnée personnelle — requête avec clé API en lecture seule | Donnée ouverte (Licence Ouverte 2.0), voir `docs/sources.md` | Clé API actuellement exposée dans le dépôt, voir Partie 5.3. |
| **API Adresse** (data.gouv.fr, gouvernement français) | Géocodage des points de repère (mairies) lors de la préparation des données | Aucune donnée personnelle — adresses publiques des mairies | France, service public | — |
| **GitHub** | Hébergement du code source | Code du projet, historique des modifications | **[À vérifier — DSI/DPO]** | Dépôt privé. |

---

## Partie 3 — Inventaire des outils exposés à l'agent

Chaque outil est une route HTTP de notre API (`assistant/api/main.py`), appelée par ElevenLabs pendant la conversation selon ce que décide le modèle de langage. Le contrat exact de chaque outil (paramètres, format de réponse) est documenté dans `docs/spec-assistant-vocal-v0-revisee.md`, §4 — ce tableau en donne la vue d'ensemble fonctionnelle et le statut de sécurité/activation.

| Outil | Rôle | Données personnelles en entrée | Données personnelles en sortie | Statut d'activation |
|---|---|---|---|---|
| `rechercher_arret` | Identifier un arrêt de bus à partir d'un nom dit à l'oral, avec désambiguïsation par commune | Non | Non | Actif |
| `horaires_theoriques` | Donner les prochains passages théoriques (prévus, pas temps réel) à un arrêt donné | Non | Non | Actif |
| `rechercher_information` | Répondre sur les tarifs, le vélo en libre-service, le transport à la demande, les amendes, à partir d'une base de connaissance indexée | Non | Non | Actif par catégorie (commercial / VLS / TAD / amendes activables séparément) |
| `rechercher_repere` | Résoudre un lieu dit en clair (« la mairie ») vers l'arrêt le plus proche | Non | Non | Actif, expérimental |
| `calculer_itineraire` | Calculer un trajet théorique (direct ou une correspondance) entre deux arrêts | Non | Non | **Désactivé par défaut** — activable depuis le back-office, expérimental |
| `enregistrer_objet_perdu` | Enregistrer une déclaration d'objet perdu | **Oui** — prénom, nom, numéro de téléphone, email optionnel | Non (accusé d'enregistrement uniquement) | Actif |
| `demander_rappel` | Transmettre une demande de rappel à un conseiller (amende, réclamation, abonnement...) | **Oui** — prénom, nom, numéro de téléphone, email optionnel | Non | Actif (sans interrupteur dédié — porte de sortie systématiquement disponible) |
| `transferer_agent` | Signaler qu'un transfert vers un conseiller humain est nécessaire | Non directement (le contexte de la demande peut en contenir) | Non | Actif (sans interrupteur dédié) |
| `enregistrer_satisfaction` | Enregistrer si l'appelant juge que l'agent a bien répondu | Non (rattaché à un identifiant de conversation technique, pas à l'identité de l'appelant) | Non | Actif |

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

- **`ingestion/`** : pipeline hors ligne, jamais exposé à un appel en direct. Transforme le GTFS brut et le site public en données exploitables par les outils : déduction de la commune de chaque arrêt à partir de ses coordonnées (absente du GTFS source — piège connu, `CLAUDE.md`), gestion des horaires au-delà de minuit (`24:30:00` pour 0h30, autre piège connu), index phonétique pour la reconnaissance des noms d'arrêts.
- **`outils/`** : la logique métier de chaque outil décrit en Partie 3, plus `db.py` qui centralise le schéma SQLite et les migrations. Toutes les requêtes prenant une donnée externe en entrée (nom d'arrêt prononcé, identifiant reçu d'un outil précédent) utilisent des requêtes paramétrées, vérifié explicitement pour la Partie 5.1.
- **`api/`** : point d'entrée unique de tout appel externe. `main.py` déclare les routes, `schemas.py` valide chaque paramètre avant qu'il n'atteigne le code métier (Pydantic), `auth.py` vérifie le jeton ou l'authentification back-office.
- **`backoffice/`** : la seule interface humaine du projet. `appels.py` reçoit et stocke le webhook de fin d'appel (et purge désormais son contenu après 90 jours, Partie 6.4) ; `activation.py` gère l'activation progressive de chaque outil ; `exports.py` produit les exports CSV ; `page.py` génère les pages HTML consultées par l'équipe.

### 4.3 Tests et vérification

Conformément à la règle de méthode « chaque fonction s'accompagne d'un script de vérification » (1.2), le dossier `tests/` contient :

- `verifier_api.py` — vérifie chaque route d'outil contre une API déjà démarrée (authentification, réponse attendue, budget de latence de 300 ms).
- `verifier_backoffice.py` — même principe pour les routes du back-office (webhook, exports, activation).
- `verifier_horaires.py` — vérifie les calculs d'horaires contre des cas connus, notamment le piège des heures au-delà de minuit.
- `explorer_gtfs.py` — outil d'exploration manuelle des données GTFS, pour vérifier une hypothèse avant de coder dessus plutôt qu'après.
- `questions_crc.csv` / `questions_evaluation.csv` — jeux de questions réelles avec réponse attendue, utilisés par `evalcorpus.py` pour mesurer la qualité de la recherche documentaire et détecter des régressions.

Ces scripts sont relancés systématiquement avant chaque changement de code touchant l'API ou le back-office — utilisés à plusieurs reprises pendant la préparation de ce document même (Parties 5 et 6, correctifs de sécurité et de rétention).

### 4.4 Historique des anomalies trouvées et corrigées

Extrait sélectif du journal complet (`docs/prochaines-etapes.md`), pour donner à l'audit une idée concrète de la discipline de vérification appliquée tout au long du projet — pas une liste exhaustive, qui resterait dans le journal lui-même :

| Date | Anomalie | Comment trouvée | Correction |
|---|---|---|---|
| 02/09/2026 | `rechercher_information` renvoyait une erreur 502 en production | Test réel | Résolu et vérifié le jour même |
| 03/09/2026 | Régression sur le veto lexical du corpus documentaire | Mesure via `evalcorpus` | Détectée avant mise en production, annulée |
| 25/09/2026 | Latence de `calculer_itineraire` doublée par rapport au budget (300 ms) | Mesure directe en local | Cause identifiée (requête coûteuse relancée inutilement) et corrigée le jour même |
| 28/09/2026 | Le prompt citait un exemple de commune (« Marignane ») que le modèle répétait littéralement au lieu de substituer la vraie réponse de l'outil | Lecture d'un vrai transcript d'appel | Exemple reformulé pour être explicitement non littéral |
| 28/09/2026 | Deux candidats LLM testés (Gemini 3.5 Flash-Lite, Qwen3.5-397B-A17B) ont fabriqué des données (nom/téléphone inventés) ou halluciné une contrainte système, en appel réel | Analyse de charges de webhook brutes après appels de test | Aucun des deux déployé ; migration reportée le temps de tester d'autres candidats |
| 28-29/09/2026 | Gemini 3.1 Flash Lite, retenu ensuite, a montré 5 anomalies distinctes en test réel (dont une fabrication de coordonnées similaire) avant d'être jugé fiable | Même méthode, un appel réel à la fois, un correctif à la fois | Chaque anomalie corrigée et revérifiée le jour même avant de passer à la suivante — voir 4.4 pour le détail complet dans le journal |
| 29/09/2026 | Clé API exposée en clair dans des échanges de travail ; base de données propre sans politique de rétention | Relecture volontaire en préparant ce document | Jeton renouvelé et vérifié ; purge automatique à 90 jours implémentée et vérifiée le jour même (Parties 5 et 6) |

Le point commun de ces épisodes : aucune anomalie n'a été découverte par un appelant réel en dehors des tests. Toutes ont été trouvées soit par une vérification automatisée, soit par une relecture attentive d'un appel de test avant toute exposition publique plus large.

---

## Partie 5 — Sécurité

### 5.1 Principes appliqués, vérifiés dans le code au 29/09/2026

- **Authentification par jeton sur chaque route d'outil** (`assistant/api/auth.py`) : comparaison en temps constant (`secrets.compare_digest`), qui protège contre les attaques par mesure de temps de réponse — pas une simple égalité de chaînes.
- **Authentification HTTP Basic séparée sur le back-office** (`verifier_acces_backoffice`), jamais accessible depuis l'agent vocal.
- **Validation stricte de toutes les entrées** via les schémas Pydantic de FastAPI (`assistant/api/schemas.py`) : chaque paramètre reçu d'un outil est typé et contraint avant d'atteindre le code métier. Preuve concrète et datée de son utilité : le 28/09/2026, un modèle de langage testé (Gemini 3.1 Flash Lite) a tenté d'appeler `enregistrer_objet_perdu` avec `nom="Inconnu"` et `telephone="0000000000"` plutôt que de poser la question à l'appelant — bloqué le jour même par une contrainte ajoutée sur ces deux champs (longueur minimale, puis forme d'un numéro français valide). Voir `docs/prochaines-etapes.md`, entrée du 28/09.
- **Requêtes SQL exclusivement paramétrées.** Vérification explicite menée pour ce document : les trois seuls endroits du code utilisant une interpolation de chaîne dans une requête SQL (`assistant/outils/db.py`, `assistant/backoffice/exports.py`) construisent leur requête à partir de noms de table/colonne codés en dur dans le code (listes Python fixes), jamais à partir d'une donnée reçue d'un appelant ou d'un outil. Partout ailleurs (45 requêtes au total), les valeurs variables passent par des paramètres liés (`?`), la protection standard contre l'injection SQL.
- **Paramétrage externalisé** : tout ce qui est propre au réseau (source GTFS, identifiant d'agent, voix disponibles) vit dans `data/config.yaml` et des variables d'environnement, jamais codé en dur — à une exception près, voir 5.3.

### 5.2 Surface exposée

Voir Partie 3 pour le détail. En résumé : 9 routes d'outils + 2 routes de webhook accessibles publiquement (protégées par jeton), routes `/backoffice/*` accessibles publiquement mais protégées par mot de passe (jamais appelées par l'agent). Aucune base de données n'est exposée directement — les fichiers SQLite ne sont accessibles que depuis le code serveur.

**[À vérifier — DSI]** Points non contrôlés dans le cadre de ce document :
- Aucune limitation de débit (*rate limiting*) constatée dans le code : un client qui connaîtrait le jeton pourrait appeler les routes sans restriction de fréquence. Risque faible tant que le jeton reste confidentiel, mais absent comme deuxième ligne de défense.
- Chiffrement en transit (HTTPS) : Clever Cloud fournit un certificat TLS par défaut sur les domaines `*.cleverapps.io`, mais la configuration exacte (versions TLS acceptées, HSTS) n'a pas été vérifiée pour ce document.

### 5.3 Gestion des secrets

Deux catégories de secrets coexistent dans ce projet, à ne pas confondre :

- **Secrets délivrés par un fournisseur** (`ELEVENLABS_API_KEY`, la clé Mecatran du flux GTFS) : générés et reconnus par le système du fournisseur, à renouveler depuis leur propre interface.
- **`API_TOKEN`** : un secret inventé par le projet lui-même, comparé tel quel par notre propre code (`assistant/api/auth.py`). Sert à la fois de mot de passe pour les 9 outils, de jeton d'URL pour le webhook de fin d'appel, et de mot de passe du back-office — un seul secret, trois usages (voir limite en 5.4).

`.env` (qui contient `API_TOKEN` en local) est bien exclu du dépôt (`.gitignore`), vérifié.

**Incident et correction du 28/09/2026** : `API_TOKEN` a circulé en clair dans plusieurs charges de webhook collées dans des échanges de travail. Rotation effectuée aux quatre endroits qui en dépendent (variable d'environnement Clever Cloud, en-tête des 9 outils ElevenLabs, URL du webhook de fin d'appel, en-tête du webhook de personnalisation), vérifiée sur un appel réel, anciennes entrées supprimées côté ElevenLabs. Journal complet dans `docs/prochaines-etapes.md`.

**Point encore ouvert** : `data/config.yaml` est versionné par git (absent du `.gitignore`, malgré ce qu'affirme `CLAUDE.md`) et contient la clé API Mecatran du flux GTFS en clair, présente dans l'historique depuis plusieurs commits. Risque faible (accès en lecture à un flux de données ouvertes), mais à régénérer par hygiène avant l'audit, et la documentation du projet (`CLAUDE.md`) à corriger sur ce point.

**Piste d'amélioration identifiée en re-créant le webhook de fin d'appel** : le formulaire ElevenLabs propose une syntaxe `{{ variable d'environnement }}` pour l'URL des webhooks, réservée à la plateforme Agents. Actuellement, le jeton apparaît en clair dans l'URL elle-même, donc visible dans toute capture d'écran ou export de configuration — passer par cette syntaxe éviterait cette exposition. Non fait à ce jour.

### 5.4 Limites connues

- **Un seul secret pour trois usages** (outils, webhook, mot de passe back-office) : pas de séparation des privilèges. Compromettre l'un compromet les trois.
- **Rotation entièrement manuelle**, répartie sur deux plateformes externes (Clever Cloud, ElevenLabs) sans mécanisme de transition — la rotation du 28/09 a provoqué une courte interruption de service (un webhook modifié mais non publié côté ElevenLabs), révélatrice de cette fragilité opérationnelle.
- **Pas de vérification de signature HMAC** sur le webhook de fin d'appel — la sécurité repose entièrement sur le secret dans l'URL, alors qu'ElevenLabs propose HMAC nativement (secret déjà généré côté ElevenLabs, non exploité côté code).
- **Politique de rétention sur notre propre base de données : partiellement corrigée.** `appels.donnees_brutes` est purgé automatiquement après 90 jours depuis le 29/09/2026 (Partie 6.4). `objets_perdus`/`demandes_rappel` restent, eux, sans politique de rétention — décision produit encore à trancher, pas seulement technique.

### 5.5 Recommandations avant un pilote public plus large

1. Mettre en place la vérification de signature HMAC du webhook de fin d'appel.
2. Séparer le mot de passe back-office du jeton des outils.
3. Régénérer la clé Mecatran et corriger `.gitignore`/`CLAUDE.md`.
4. Trancher et implémenter une durée de rétention pour `objets_perdus`/`demandes_rappel` (Partie 6.4) — `appels` déjà fait.
5. Envisager une limitation de débit basique si le périmètre d'appel s'élargit.

---

## Partie 6 — RGPD et données personnelles

### 6.1 Données personnelles collectées

| Source | Données | Table / emplacement |
|---|---|---|
| Déclaration d'objet perdu | Prénom, nom, téléphone, email (optionnel) | `objets_perdus` (base `data/etat/assistant.db`) |
| Demande de rappel | Téléphone, prénom/nom (optionnel), email (optionnel), motif, résumé de la demande | `demandes_rappel` (même base) |
| **Chaque appel, sans exception** | **Transcript intégral de la conversation (donc tout nom, téléphone, description d'objet énoncé à l'oral, même sans déclaration formelle), numéro de l'appelant, identifiants d'appel** | `appels.donnees_brutes` (même base) — charge JSON complète reçue d'ElevenLabs, stockée telle quelle |
| Côté ElevenLabs (hors de notre infrastructure) | Audio de l'appel, transcript, mêmes métadonnées | Infrastructure ElevenLabs — rétention désormais réglée à 365 jours avec suppression automatique (28/09/2026) |

### 6.2 Finalités

- `objets_perdus` / `demandes_rappel` : traiter la demande concrète de l'appelant (retrouver un objet, être rappelé par un conseiller).
- `appels.donnees_brutes` : traçabilité économique et environnementale du projet (coût, tokens, minutes voix — exigence explicite de `CLAUDE.md`), suivi qualité, débogage.

**Point de vigilance (minimisation des données)** : la finalité de traçabilité ne nécessite que des métriques (coût, durée, modèle utilisé) — déjà extraites dans des colonnes dédiées de la table `appels`. Le fait de conserver *en plus* la charge JSON brute intégrale, transcript inclus, va au-delà de cette finalité. C'est un choix de conception compréhensible (déboguer un comportement d'agent nécessite de revoir la conversation complète, comme on l'a fait à de nombreuses reprises pendant ce projet), mais qui doit être assumé explicitement et borné dans le temps plutôt que subi par défaut.

### 6.3 Base légale — **[À qualifier — DPO]**

Hypothèses de travail, à valider formellement :
- Traitement des déclarations (objets perdus, rappels) : probablement l'exécution d'une démarche demandée par la personne elle-même.
- `opt_in_marketing` : consentement explicite déjà recueilli et respecté dans le code (question posée une seule fois après l'enregistrement, un refus n'est jamais reproposé — voir `docs/spec-assistant-vocal-v0-revisee.md`, section Opt-in marketing).
- Conservation du transcript complet dans `appels` : base légale à qualifier spécifiquement, distincte de celle des déclarations elles-mêmes.

### 6.4 Durées de conservation

- **ElevenLabs : corrigé le 28/09/2026.** Rétention 365 jours, suppression automatique de la transcription/PII et de l'audio après ce délai, appliquée aux conversations existantes. Vérifié sur un appel réel (`deletion_time_unix_secs` renseigné, `delete_transcript_and_pii: true`, `delete_audio: true`).
- **`appels.donnees_brutes` : corrigé le 29/09/2026.** Purge automatique (transcript intégral, numéro de l'appelant) après 90 jours, sans supprimer la ligne ni les métriques déjà extraites (`duree_secs`, `cout_usd`, `minutes_asr`/`tts`, `modeles_llm`, `tokens_llm`...), qui restent disponibles indéfiniment comme l'exige `CLAUDE.md`. Purge exécutée au démarrage de l'application puis une fois par jour tant qu'elle tourne (`assistant/backoffice/appels.py`, `purger_transcripts_expires`). Vérifié en local : un appel de 100 jours voit son contenu vidé, un appel récent reste intact, et un recalcul des métriques après purge (`retraiter_tracabilite`) ne les écrase pas — garde-fou ajouté à cette occasion. Durée de 90 jours choisie comme compromis entre le besoin de suivi qualité de l'équipe (relecture d'un appel récent) et la minimisation des données.
- **`objets_perdus` / `demandes_rappel` : encore ouvert.** Une fonction de suppression existe (`supprimer_objet_perdu`) mais reste un geste manuel, prévue à l'origine pour nettoyer des données de test, pas comme mécanisme de conformité systématique. Contrairement au transcript d'appel, ces données restent activement utiles tant que la demande n'est pas résolue (objet retrouvé, rappel effectué) — la durée de rétention appropriée dépend donc d'une décision produit (combien de temps une recherche d'objet perdu reste active ?) plutôt que d'un choix purement technique. **Reste à trancher avec l'utilisateur avant l'audit.**

### 6.5 Sous-traitants et transferts hors UE

Voir Partie 2.4 pour le détail par fournisseur. Synthèse : ElevenLabs, Twilio et le fournisseur du modèle de langage (Google ou OpenAI selon le modèle retenu) sont des sociétés non européennes dont la localisation exacte de traitement n'a pas été vérifiée contractuellement — **[À vérifier — DSI/DPO]** avant tout traitement de données réelles d'appelants publics.

### 6.6 Droits des personnes

**[À formaliser — DSI/DPO]** Aucun mécanisme self-service n'existe aujourd'hui pour qu'un appelant demande l'accès, la rectification ou l'effacement de ses données. Une demande serait traitée aujourd'hui par une intervention manuelle en base de données par l'équipe technique — un processus à documenter formellement avant l'ouverture d'un pilote public, y compris le délai de réponse et le canal de demande.

### 6.7 Mesures de sécurité des données personnelles

Voir Partie 5 pour le détail complet (authentification, validation des entrées, requêtes paramétrées). Aucune mesure spécifique de chiffrement au repos des données personnelles dans la base SQLite au-delà de ce que fournit Clever Cloud par défaut — **[À vérifier — DSI]**.

### 6.8 Éléments pour l'analyse d'impact (AIPD)

Ce document fournit la matière première ; l'analyse elle-même reste à mener par le DPO. Points qu'elle devra couvrir en priorité, par ordre d'importance selon ce qui a été trouvé en préparant ce dossier :
1. Valider la durée de rétention retenue pour `appels.donnees_brutes` (90 jours, corrigé le 29/09/2026 — Partie 6.4) et trancher celle de `objets_perdus`/`demandes_rappel`, encore ouverte.
2. La qualification de la base légale pour chaque table (6.3).
3. Les transferts hors UE vers ElevenLabs, Twilio et le fournisseur de modèle de langage (6.5).
4. La formalisation des droits des personnes (6.6).

---

## Partie 7 — Traçabilité et gouvernance

### 7.1 Traçabilité économique et environnementale

Exigence non négociable du projet, telle que formulée dans `CLAUDE.md` :

> Chaque appel logge le modèle utilisé, les tokens consommés, les minutes de reconnaissance et de synthèse vocale, et le coût estimé. Ces données servent à l'évaluation économique et environnementale du projet, elles ne sont pas reconstituables après coup.

Concrètement, huit colonnes dédiées sur la table `appels` (`assistant/backoffice/appels.py`, `_extraire_tracabilite`), extraites automatiquement de chaque webhook de fin d'appel : durée, coût réel (pas estimé — la valeur facturée par ElevenLabs), minutes de reconnaissance et de synthèse vocale séparément, détail des modèles de langage utilisés (utile quand un appel bascule sur un modèle de secours, voir 4.4), tokens consommés, outils réellement appelés, voix utilisées. Ces colonnes ne contiennent aucune donnée personnelle et ne sont jamais concernées par la purge de 90 jours (Partie 6.4) — c'est précisément ce qui permet de purger le reste sans violer l'exigence de traçabilité ci-dessus.

Une fonction de secours, `retraiter_tracabilite`, permet de recalculer ces colonnes depuis `donnees_brutes` si la logique d'extraction est corrigée après coup (par exemple si un nouveau type d'appel a un format légèrement différent, déjà arrivé une fois). Elle ne fonctionne que sur les appels dont `donnees_brutes` n'a pas encore été purgé — une fenêtre de 90 jours pour corriger une erreur d'extraction, au-delà les métriques déjà calculées restent figées.

`resumer_tracabilite` agrège ces données pour le tableau de bord du back-office (durée moyenne, coût total, répartition des outils utilisés, horaire moyen des appels) — l'outil de pilotage économique du projet au jour le jour.

**Deux mécanismes de retour distincts, à ne pas confondre :**
- **Satisfaction déclarée par l'appelant** (`satisfaction_appels`, outil `enregistrer_satisfaction`) : une réponse oui/non par conversation, posée une seule fois en fin d'appel, jamais avant que l'appelant ait explicitement répondu (correction du 28/09/2026, Partie 4.4).
- **Évaluation de l'équipe** (`evaluations_appels`, back-office) : un humain relit un appel et le juge « bonne » ou « mauvaise » réponse, avec une note libre optionnelle. Plusieurs évaluations possibles par appel, jamais d'écrasement d'un avis précédent — l'historique complet reste consultable.

### 7.2 Activation progressive des outils

Chaque outil (Partie 3) peut être coupé indépendamment depuis le back-office, plus un interrupteur général (`activation_outils`, clé `"tous"`) qui coupe tout d'un coup si nécessaire. Trois raffinements notables :

- **`calculer_itineraire`/`rechercher_repere` démarrent désactivés par défaut** (`_OUTILS_INACTIFS_PAR_DEFAUT`, `assistant/outils/db.py`) — la fonctionnalité expérimentale d'itinéraire ne s'active jamais automatiquement à un nouveau déploiement, elle doit être explicitement rallumée.
- **`rechercher_information` s'active par catégorie** (commercial, vélo en libre-service, transport à la demande, amendes) plutôt que d'un bloc — aligné sur la grille de classification réelle utilisée par l'équipe CRC, pas sur un découpage technique arbitraire. Un réseau peut par exemple couper le vélo en libre-service sans couper les tarifs.
- **Un outil désactivé renvoie une erreur HTTP 503**, pas une réponse habillée en « rien trouvé ». Choix délibéré, vérifié en conditions réelles avant d'être retenu : à chaque fois qu'un outil a échoué techniquement en test (404, 422...), l'agent vocal a basculé proprement vers la sortie (transfert ou rappel) sans jamais inventer de réponse — plutôt que de fabriquer une réponse « vide » différente pour chacun des contrats de sortie possibles, au risque de s'y contredire, le projet réutilise ce comportement déjà éprouvé.

Conséquence directe pour la confiance de l'appelant : le message d'accueil de l'agent ne promet jamais une capacité coupée. La variable dynamique `outils_actifs` (webhook de personnalisation, Partie 2.1) est recalculée à chaque appel à partir de l'état réel de l'activation back-office — si un outil est coupé, il disparaît du message d'accueil, pas seulement du comportement.

### 7.3 Méthode de test et d'amélioration continue

Deux boucles de mesure distinctes, toutes deux documentées dans le dépôt avant même d'être utilisées :

**Mesure automatisée de la recherche documentaire** (`assistant/evalcorpus.py`) : un jeu de questions réelles avec la bonne réponse attendue (`tests/questions_evaluation.csv`) donne un taux de réussite chiffré, comparable dans le temps — l'instrument qui a permis de détecter une régression avant mise en production (4.4) plutôt que de la découvrir par un appelant.

**Remontée des vrais besoins par l'équipe CRC** (`docs/methode-amelioration-continue.md`), avec une contrainte RGPD posée dès la conception : l'équipe note **une ligne reformulée** (« ce qu'un appelant a demandé, sans aucune donnée personnelle »), jamais une transcription ni un enregistrement. C'est délibérément ce geste de reformulation humaine, fait dans l'instant, qui évite d'avoir besoin d'une AIPD ou de l'accord du DPO pour ce mécanisme précis — aucune donnée de voyageur n'en sort jamais. Ces questions alimentent le même instrument de mesure (`evalcorpus`), et chaque échec se classe dans une grille à trois catégories qui structure la correction : trou de vocabulaire (la réponse existe, sous un autre nom), trou de contenu (la réponse n'existe nulle part dans la base de connaissance), ou vraie question hors périmètre (la bonne réponse est un transfert humain, pas une page).

**Test en appel réel avant toute décision structurante** : au-delà de ces deux boucles, chaque changement de modèle de langage candidat a été validé par des appels réels sur des scénarios ciblés, avec analyse systématique de la charge JSON brute du webhook (pas seulement de ce qui s'est entendu à l'oral) — c'est cette méthode qui a permis de disqualifier deux candidats sur des fabrications de données invisibles à l'écoute d'un appel normal, et de trouver puis corriger cinq anomalies distinctes sur le candidat finalement retenu, le jour même de chaque découverte (4.4). Aucune bascule en production sans ce passage par un test réel.

---

*Suite prévue : annexes (glossaire, références officielles, extraits de code complets, schémas).*
