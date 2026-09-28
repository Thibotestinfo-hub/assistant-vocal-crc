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
- **Aucune politique de rétention sur notre propre base de données** — développé en détail en Partie 6.4, c'est le point le plus significatif de ce document.

### 5.5 Recommandations avant un pilote public plus large

1. Mettre en place la vérification de signature HMAC du webhook de fin d'appel.
2. Séparer le mot de passe back-office du jeton des outils.
3. Régénérer la clé Mecatran et corriger `.gitignore`/`CLAUDE.md`.
4. Définir et implémenter une politique de rétention/suppression sur `appels`, `objets_perdus`, `demandes_rappel` (Partie 6.4).
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
- **Notre propre base de données : aucune politique de rétention, sur aucune des trois tables.** Ni `appels` (aucune fonction de suppression n'existe dans le code, vérifié explicitement pour ce document), ni `objets_perdus`/`demandes_rappel` (une fonction de suppression existe — `supprimer_objet_perdu` — mais reste un geste manuel non systématisé, prévue à l'origine pour nettoyer des données de test, pas comme mécanisme de conformité). **C'est le point le plus important de ce chapitre** : corriger ElevenLabs ne suffit pas, une copie complète et permanente de chaque conversation reste sur notre propre serveur.

### 6.5 Sous-traitants et transferts hors UE

Voir Partie 2.4 pour le détail par fournisseur. Synthèse : ElevenLabs, Twilio et le fournisseur du modèle de langage (Google ou OpenAI selon le modèle retenu) sont des sociétés non européennes dont la localisation exacte de traitement n'a pas été vérifiée contractuellement — **[À vérifier — DSI/DPO]** avant tout traitement de données réelles d'appelants publics.

### 6.6 Droits des personnes

**[À formaliser — DSI/DPO]** Aucun mécanisme self-service n'existe aujourd'hui pour qu'un appelant demande l'accès, la rectification ou l'effacement de ses données. Une demande serait traitée aujourd'hui par une intervention manuelle en base de données par l'équipe technique — un processus à documenter formellement avant l'ouverture d'un pilote public, y compris le délai de réponse et le canal de demande.

### 6.7 Mesures de sécurité des données personnelles

Voir Partie 5 pour le détail complet (authentification, validation des entrées, requêtes paramétrées). Aucune mesure spécifique de chiffrement au repos des données personnelles dans la base SQLite au-delà de ce que fournit Clever Cloud par défaut — **[À vérifier — DSI]**.

### 6.8 Éléments pour l'analyse d'impact (AIPD)

Ce document fournit la matière première ; l'analyse elle-même reste à mener par le DPO. Points qu'elle devra couvrir en priorité, par ordre d'importance selon ce qui a été trouvé en préparant ce dossier :
1. Le risque que représente la conservation permanente et intégrale du transcript de chaque appel dans `appels.donnees_brutes` (Partie 6.4) — le point le plus significatif.
2. La qualification de la base légale pour chaque table (6.3).
3. Les transferts hors UE vers ElevenLabs, Twilio et le fournisseur de modèle de langage (6.5).
4. La formalisation des droits des personnes (6.6).

---

*Suite prévue : Partie 1 (intention et genèse), Partie 4 (code source), Partie 7 (traçabilité), annexes.*
