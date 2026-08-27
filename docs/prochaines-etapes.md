# Prochaines étapes — état au 26/08/2026

Ce document sert de point de reprise après une pause. Mis à jour après une
session longue et dense sur le back-office (redesign en 2 onglets fidèle à
la maquette de l'équipe, traçabilité voix, transcription lisible) — voir
l'historique Git pour le détail des commits.

## Où on en est

- **Pipeline vocal** : inchangé depuis le 19/08 — les 6 outils fonctionnent,
  testés en conditions réelles.
- **Déploiement Clever Cloud** : stable, déploiement automatique depuis
  GitHub (`main`) confirmé fonctionnel.
- **Back-office** : entièrement refondu en 2 onglets ("Live" / "Suivi"),
  fidèle à la maquette PDF de l'équipe (pleine largeur, vrais interrupteurs,
  bouton d'arrêt en anneau, tableau + panneau de détail, diagramme en
  anneau pour la répartition des motifs). Détail des chantiers ci-dessous.

## A. Expérience voyageur (voix)

- [x] **"Collège F. Léger" non corrigé malgré une règle présente** —
      cause trouvée (27/08) : les 18 abréviations avec un point dans le
      dictionnaire cassaient la correspondance côté ElevenLabs. Corrigé
      en développant nous-mêmes ces noms avant de les renvoyer à l'agent
      (`assistant/ingestion/prononciation.py`), sans dépendre de ce
      mécanisme ElevenLabs. Vérifié sur les 18 entrées via
      `rechercher_arret()`.
- [x] **"Chateau de la Pl"** — confirmé par l'utilisateur : "Château de la
      Plantade". Ajouté à `data/prononciation.pls` et actif immédiatement.
- [x] **"Est-ce que bien de l'arrêt X qu'il s'agit"** — source trouvée
      dans le prompt système (section "Identifier un arrêt", cas
      "confiance moyenne") : le modèle paraphrase l'exemple donné au lieu
      de le reprendre tel quel. Consigne ajoutée au prompt côté ElevenLabs
      le 27/08 ("reprends cette formulation telle quelle, mot pour mot").
      **À vérifier au prochain test téléphonique** : pas de garantie
      qu'un LLM suive une consigne à 100 %.
- [ ] **Latence perçue** signalée comme un peu longue en test vocal — à
      objectiver (mesurer précisément où le temps passe) avant de chercher
      à l'améliorer. Prévu au protocole de test téléphonique (E).
- [ ] Continuer le cycle mesure-ajustement sur la prononciation au fil des
      tests — ce n'est jamais "terminé" (voir CLAUDE.md, pièges connus).
      Nouveau point relevé en scannant tout le GTFS (27/08) : "Chemin des
      Pinet" ressemblait à un nom tronqué mais n'en est pas un — c'est un
      nom de *station* GTFS, jamais renvoyé par nos outils (le véritable
      arrêt embarquable s'appelle "Pinettes", un mot complet). Aucune
      action nécessaire, gardé en note pour ne pas se reposer la question.
- [ ] **Discuter à qui revient la maintenance du dictionnaire de
      prononciation à terme** : l'équipe de chaque réseau connaît mieux
      que nous la prononciation locale — un outil d'édition existe
      maintenant côté back-office (voir B, onglet Prononciation), ce qui
      rend ce transfert plus concret à envisager.

## B. Expérience équipe (back-office)

### Fait cette session (26/08/2026)

- [x] **Refonte complète en 2 onglets**, fidèle à la maquette PDF fournie
      par l'équipe (après un premier essai jugé trop éloigné) : pleine
      largeur, onglets pleine largeur bleu/teal, bouton d'arrêt général en
      anneau, interrupteurs à bille pour chaque outil, info-bulles.
- [x] **Changement de voix depuis le back-office**, sans compte
      ElevenLabs côté équipe : sélecteur de voix (Lucie/Hugo/Jade) +
      curseurs **ton** (stability) et **style** (autre), tous deux
      confirmés comme de vrais champs de l'API ElevenLabs et appliqués via
      `changer_reglages_voix()`.
- [x] **Écoute d'une voix avant de l'appliquer** (picto haut-parleur,
      demandé par l'équipe) : récupère l'échantillon audio ElevenLabs à la
      demande, jamais mis en cache (certaines URLs, pour les voix
      "custom", sont probablement à durée de vie limitée).
      **⚠️ Bug ouvert** : ne fonctionne pas encore en production ("Impossible
      de lire cet extrait"). Cause probable : `ELEVENLABS_API_KEY` absente
      des variables d'environnement Clever Cloud — jamais vérifié
      explicitement. Un log a été ajouté (`print` visible dans l'onglet
      Logs de Clever Cloud) pour diagnostiquer précisément au prochain
      essai. **Premier réflexe à la reprise : vérifier l'onglet
      "Environment variables" de Clever Cloud, puis retenter et lire le
      log.**
- [x] **"Appels en cours"** construit sur une vraie vérification de l'API
      ElevenLabs (`GET /v1/convai/conversations`, testée en direct via
      Codespaces) : source de l'appel (téléphone/test) et durée écoulée.
      Interrogé à chaque affichage de l'onglet Live, timeout court (5 s),
      dégrade proprement si ElevenLabs est indisponible.
- [x] **Indicateurs "Suivi"** réorganisés en tuiles (picto + chiffre
      agrandis, 3 par ligne) ; la répartition par motif est devenue un
      vrai diagramme en anneau (SVG fait main, pas de librairie) avec
      légende, à la place d'une tuile texte.
- [x] **Tableau des demandes de rappel affiché directement** (nom,
      téléphone, heure d'appel, motif, opt-in marketing) avec export CSV —
      remplace l'ancien export "contacts marketing" qui mélangeait objets
      perdus et demandes de rappel sans valeur ajoutée réelle.
- [x] **Panneau de détail d'un appel** : s'ouvre en dessous du tableau (et
      non plus sur le côté) pour que les deux tables du Suivi fassent
      strictement la même largeur ; bouton de fermeture ajouté ; affiche
      maintenant une **vraie transcription lisible** (bulles Appelant /
      Assistant) en plus de la charge JSON brute.
      **À vérifier** : le rendu s'appuie sur les champs `role`/`message`
      documentés par ElevenLabs, pas encore reconfirmés sur un payload
      réel complet depuis un environnement avec accès réseau — à
      contrôler sur un vrai appel récent.

### Fait le 27/08/2026

- [x] **Onglet "Prononciation" dans le back-office** : dictionnaire éditable
      sans passer par ElevenLabs — le levier de paramétrage prioritaire
      identifié la veille. Ajout/suppression de règles, persistantes
      (table `regles_prononciation` dans `data/etat/assistant.db`,
      survit aux déploiements contrairement au fichier `.pls`),
      appliquées immédiatement à `rechercher_arret`. Dictionnaire de
      référence (`data/prononciation.pls`, 324 règles) affiché en lecture
      seule avec filtre.
      **Limite connue** : ne synchronise pas (encore) le dictionnaire
      ElevenLabs lui-même — nécessite l'identifiant de ce dictionnaire,
      pas encore récupéré.
- [x] **Évaluation par appel — décision de garder le binaire** (bonne/
      mauvaise + note libre) plutôt qu'une échelle, pour ce POC : le
      volume d'appels ne justifie pas la granularité, et la note libre
      capture déjà l'essentiel. Sujet à rouvrir si le volume augmente.
- [x] **Clarifié : aucun sondage de satisfaction côté appelant** (téléphone
      ou SMS) n'a jamais été prompté ni construit — vérifié dans la spec
      et le prompt système. Reste un sujet ouvert si l'équipe le souhaite
      (ferait probablement l'objet d'un chantier à part, la capacité SMS
      n'étant pas câblée dans le projet).
- [x] **Clarifié : le like/dislike ne fait pas "apprendre" le bot
      automatiquement** — aucun mécanisme de fine-tuning accessible côté
      ElevenLabs. Le vrai cycle est médié par un humain : relecture →
      pattern repéré → modification manuelle (prompt, dictionnaire,
      base de connaissance) → déploiement. C'est exactement ce qui a été
      fait cette session (le prompt "Est-ce que bien...", ci-dessus).
      Piste non développée : agréger les notes des mauvaises évaluations
      par thème pour accélérer la relecture humaine — à construire si
      utile une fois le volume d'appels réel connu.

### Restant

- [ ] **Corriger le bug d'écoute des voix** (voir ci-dessus) — probablement
      une variable d'environnement à ajouter sur Clever Cloud.
- [ ] **Vérifier la transcription sur un vrai appel** une fois le bug
      voix réglé (les deux passent par le même mécanisme de vérification
      qu'avant : coller un payload réel ou observer un appel récent).
- [ ] **Concurrence d'appels simultanés** — remonté comme un vrai
      prérequis du POC (pas juste une curiosité) : le nombre d'appels
      qu'ElevenLabs peut gérer en parallèle dépend du plan d'abonnement,
      jamais vérifié dans le dashboard. À faire avant le test live : (1)
      vérifier la limite affichée côté ElevenLabs (Paramètres/Abonnement),
      (2) tester réellement 2-3 appels simultanés (téléphone ou widget)
      pour confirmer que notre back-end encaisse sans souci.
- [ ] **Synchroniser le dictionnaire de prononciation vers ElevenLabs**
      (voir ci-dessus) : récupérer l'identifiant du dictionnaire déjà
      publié côté ElevenLabs, puis appeler leur API `add-rules` depuis
      le bouton "Ajouter" du back-office.
- [ ] **Curseurs "ton"/"style"** : fonctionnels mais leur valeur par défaut
      ne reflète pas le réglage réellement en place (page volontairement
      indépendante d'ElevenLabs au chargement) — à surveiller à l'usage,
      pas gênant en soi mais à expliquer à l'équipe CRC.
- [ ] **Numéro Twilio français** : les exigences françaises ont été
      significativement simplifiées par Twilio en septembre 2025 (plus
      besoin de pièce d'identité ni de preuve d'autorisation — juste un
      K-bis, l'email du représentant, un site web/page entreprise). Coût
      quasi nul pour l'utilisateur (forfait illimité Europe) contre un
      numéro US potentiellement coûteux à plusieurs tests en parallèle.
      À confirmer dans la console Twilio avant de se lancer (recherche
      web uniquement, pas de lecture directe de la doc Twilio possible
      depuis cet environnement).

## C. Dupliquer pour un autre réseau (nouveau chantier, pas commencé)

Discuté avec l'équipe : une fois B stabilisé **et sécurisé** (voir revue de
sécurité ci-dessous), un autre réseau du groupe pourrait vouloir tester
l'outil en parallèle.

- Le code est déjà pensé pour être dupliqué par paramétrage (`config.yaml`
  : GTFS, agent ElevenLabs, voix) — dupliquer aujourd'hui = un nouveau
  déploiement Clever Cloud + nouveau `config.yaml` + nouvel agent
  ElevenLabs + numéro Twilio, fait à la main.
- Une vraie page self-service ("upload tes documents, connecte ton GTFS en
  quelques clics") est un **projet à part**, plus gros — ne pas s'y lancer
  avant d'avoir fait une duplication manuelle au moins une fois, pour
  savoir ce qui est réellement pénible à refaire et donc ce qui vaut la
  peine d'être automatisé.
- Le point dur identifié : automatiser la construction de la base de
  connaissance (FAQ) à partir d'un document déposé par un réseau. Faisable
  en principe, mais doit garder une relecture humaine avant mise en prod
  (règle d'exactitude : jamais de réponse non vérifiée à un voyageur).
- **Recommandation** : si un deuxième réseau est vraiment partant, faire la
  duplication manuelle en premier — rapide, prouvé, sans risque — avant
  d'envisager un outil dédié.

## D. Reporté à la fin du projet

- [ ] **Revue de sécurité complète**, notamment :
  - la vérification de la signature HMAC du webhook ElevenLabs (non
    vérifiée actuellement, décision explicite pour avancer plus vite) ;
  - les permissions larges accordées à la clé API ElevenLabs utilisée
    depuis Codespaces ("quasiment toutes les cases cochées") — à revoir
    et restreindre au strict nécessaire.

## E. Protocole de test téléphonique réel (à préparer en premier demain)

Demande explicite de l'utilisateur (26/08, fin de session) : avant
d'attaquer autre chose, refaire un vrai test en conditions réelles, sur le
numéro Twilio (pas seulement le widget), avec un protocole complet et
étapé — probablement pour objectiver les points ouverts sur la latence
perçue (A) et remonter de nouveaux cas de prononciation. À construire en
premier au démarrage de la prochaine session : scénarios d'appel (chaque
outil au moins une fois, y compris un cas d'erreur/hors périmètre), points
de mesure (latence perçue, prononciation, transfert humain), et grille de
recueil des résultats — probablement consignée ensuite dans le back-office
(évaluation par appel, déjà existante) plutôt que sur un support à part.

## Suggestion pour la reprise

1. **Construire le protocole de test téléphonique** (E ci-dessus) — c'est
   la demande explicite pour démarrer la session.
2. **Corriger le bug d'écoute des voix** — vérifier la variable
   d'environnement `ELEVENLABS_API_KEY` sur Clever Cloud en premier, avant
   toute autre hypothèse (c'est la cause la plus probable). Utile avant le
   test réel si l'équipe veut aussi valider la voix ce jour-là.
3. Une fois corrigé, vérifier au passage que la transcription (bulles
   Appelant/Assistant) s'affiche correctement sur un vrai appel.
4. Avant le test live : vérifier la limite de concurrence ElevenLabs et la
   tester réellement.
5. Ensuite, au choix : le dictionnaire de prononciation depuis le
   back-office (C, prioritaire côté "paramétrable sans ElevenLabs"), ou les
   points de prononciation encore ouverts (A).
