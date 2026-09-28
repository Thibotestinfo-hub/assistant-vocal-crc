# Dossier d'audit DSI — Assistant vocal, zone Étang

Document en construction, chapitre par chapitre, pour l'audit interne DSI précédant un pilote public sur une filiale. Structure complète et méthode de rédaction actées avec l'utilisateur le 29/09/2026 (voir `docs/prochaines-etapes.md`).

Chaque affirmation de ce document vient d'un fichier réel du dépôt, du code lui-même, ou d'une vérification technique directe. Quand un fait ne peut pas être vérifié depuis le dépôt seul (contrats fournisseurs, localisation exacte de serveurs tiers...), il est marqué **[À vérifier — DSI/DPO]** plutôt qu'affirmé.

Statut : parties 2 et 3 rédigées. Parties 1, 4 à 7 et annexes à venir.

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

*Suite prévue : Partie 1 (intention et genèse), Partie 4 (code source), Partie 5 (sécurité — y compris les deux points ouverts déjà identifiés), Partie 6 (RGPD), Partie 7 (traçabilité), annexes.*
