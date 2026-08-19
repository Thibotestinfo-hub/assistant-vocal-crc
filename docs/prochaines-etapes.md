# Prochaines étapes — état au 19/08/2026

Ce document sert de point de reprise après une pause. Écrit à la fin d'une
session qui a réglé plusieurs incidents de déploiement et refondu le
back-office — voir l'historique Git pour le détail des commits.

## Où on en est

- **Pipeline vocal** : les 6 outils fonctionnent, testés en conditions
  réelles (widget ElevenLabs). Bugs trouvés et corrigés : ordre du prompt
  objets perdus, fuseau horaire, synonyme "titre unitaire" manquant.
- **Déploiement Clever Cloud** : stable. `corpus_index.json` est versionné
  (évite de recalculer les embeddings à chaque déploiement) ;
  `assistant.db` persiste maintenant via un FS Bucket (`data/etat/`,
  chemin relatif au dossier de l'application — piège rencontré : ne pas
  utiliser de chemin absolu malgré ce que suggèrent les logs Clever Cloud).
- **Dictionnaire de prononciation** : 323 règles (`data/prononciation.pls`),
  construites à partir d'une relecture systématique de tous les arrêts
  GTFS, uploadées et publiées côté ElevenLabs (Paramètres de l'espace de
  travail → Webhook post-appel → Voix → Dictionnaires de prononciation,
  pas "Développeurs > Webhooks" qui est un piège différent, sans rapport).
- **Back-office** : refondu en une seule page (historique des appels en
  accordéon, panneau d'activation des outils, exports CSV, compteurs).
  Palette de couleurs de l'équipe appliquée en première mouture — jugée
  perfectible, à retravailler ensemble.

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
      improvisation du modèle (Gemini 2.5 Flash), soit d'un réglage
      "Comportement de l'agent" à inspecter côté ElevenLabs.
- [ ] **Latence perçue** signalée comme un peu longue en test vocal — à
      objectiver (mesurer précisément où le temps passe : reconnaissance,
      LLM, synthèse) avant de chercher à l'améliorer.
- [ ] Continuer le cycle mesure-ajustement sur la prononciation au fil des
      tests — ce n'est jamais "terminé" (voir CLAUDE.md, pièges connus).

## B. Expérience équipe (back-office)

- [ ] **Itérer sur le design** : première mouture posée aujourd'hui,
      l'équipe CRC veut continuer à l'affiner (couleurs, disposition).
- [ ] **Traçabilité par appel** (CLAUDE.md, contrainte non négociable,
      jamais implémentée) : logger modèle utilisé, tokens consommés,
      minutes de reconnaissance et de synthèse vocale, coût estimé, pour
      chaque appel. C'est un vrai chantier technique (webhook ElevenLabs
      et/ou API d'usage), pas juste un ajout d'affichage — mais c'est ce
      qui débloque les 4 compteurs actuellement en "à venir" sur le
      back-office (durée moyenne d'appel, horaire moyen, répartition par
      type de requête, coût/impact carbone).
- [ ] **Vérifier le format réel du webhook de fin d'appel** : jamais
      inspecté avec un vrai payload (toujours contourné faute d'accès
      réseau à elevenlabs.io pendant l'écriture du code). Nécessaire pour
      fiabiliser `assistant/backoffice/appels.py`, actuellement défensif.
      Un appel de test suffit, à faire au retour.
- [ ] **Idée à évaluer : changer de voix depuis notre back-office**,
      sans que l'équipe CRC ait besoin de se connecter à ElevenLabs
      pendant le POC (2-3 voix au choix). Techniquement : appeler l'API
      ElevenLabs pour modifier le `voice_id` de l'agent, depuis un petit
      formulaire chez nous, avec une clé API ElevenLabs stockée côté
      serveur. Faisable, mais un vrai morceau (nouvelle intégration API,
      gestion du secret) — à chiffrer avant de s'engager, ce n'est peut-être
      pas prioritaire pour un POC.

## C. Reporté à la fin du projet

- [ ] **Revue de sécurité complète**, notamment la vérification de la
      signature HMAC du webhook ElevenLabs (actuellement non vérifiée,
      décision explicite pour avancer plus vite pendant le
      développement).

## Suggestion pour la reprise

Vu la taille du chantier B (traçabilité), ce serait sans doute la première
chose à cadrer ensemble au retour — c'est ce qui bloque une bonne partie
des attentes exprimées côté back-office (compteurs, coût, carbone). Le
reste (points de prononciation, design) peut avancer par petites touches
en parallèle.
