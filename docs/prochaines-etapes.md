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

- [ ] **"Collège F. Léger" non corrigé par le dictionnaire** malgré une
      règle présente : tester d'autres entrées avec un point dans
      l'abréviation (ex. "GS P. Picasso", "Collège C. Claud", "Collège E.
      Mirab") pour savoir si c'est systématique (le point casserait la
      correspondance côté ElevenLabs) ou un cas isolé.
- [ ] **"Chateau de la Pl"** : nom tronqué dans le GTFS, resté sans alias
      (la cellule du fichier contenait une note, pas un vrai alias) —
      vérifier le nom complet sur le site du réseau ou une carte, puis
      compléter `data/prononciation.pls`.
- [ ] **"Est-ce que bien de l'arrêt X qu'il s'agit"** : faute de français
      entendue en test, absente de nos fichiers — vient soit d'une
      improvisation du modèle, soit d'un réglage "Comportement de l'agent"
      à inspecter côté ElevenLabs.
- [ ] **Latence perçue** signalée comme un peu longue en test vocal — à
      objectiver (mesurer précisément où le temps passe) avant de chercher
      à l'améliorer.
- [ ] Continuer le cycle mesure-ajustement sur la prononciation au fil des
      tests — ce n'est jamais "terminé" (voir CLAUDE.md, pièges connus).
- [ ] **Discuter à qui revient la maintenance du dictionnaire de
      prononciation à terme** : l'équipe de chaque réseau connaît mieux
      que nous la prononciation locale — évaluer un transfert de cette
      tâche vers eux une fois un outil d'édition en place (voir point C
      "dictionnaire depuis le back-office" ci-dessous).

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
- [ ] **Dictionnaire de prononciation depuis le back-office** : prochain
      levier de paramétrage identifié avec l'équipe (ElevenLabs expose une
      API pour ça, `/v1/pronunciation-dictionaries`) — même logique que le
      changement de voix. Priorité proposée pour la suite de ce chantier
      "paramétrable sans ElevenLabs".
- [ ] **Curseurs "ton"/"style"** : fonctionnels mais leur valeur par défaut
      ne reflète pas le réglage réellement en place (page volontairement
      indépendante d'ElevenLabs au chargement) — à surveiller à l'usage,
      pas gênant en soi mais à expliquer à l'équipe CRC.

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

## Suggestion pour la reprise

1. **Corriger le bug d'écoute des voix** — vérifier la variable
   d'environnement `ELEVENLABS_API_KEY` sur Clever Cloud en premier, avant
   toute autre hypothèse (c'est la cause la plus probable).
2. Une fois corrigé, vérifier au passage que la transcription (bulles
   Appelant/Assistant) s'affiche correctement sur un vrai appel.
3. Avant le test live : vérifier la limite de concurrence ElevenLabs et la
   tester réellement.
4. Ensuite, au choix : le dictionnaire de prononciation depuis le
   back-office (C, prioritaire côté "paramétrable sans ElevenLabs"), ou les
   points de prononciation encore ouverts (A).
