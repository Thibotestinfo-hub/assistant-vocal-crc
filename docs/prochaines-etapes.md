# Prochaines étapes — état au 02/09/2026

## ✅ Résolu ce soir — rechercher_information (502 en production)

Constaté le 02/09 : `POST /outils/rechercher_information` renvoyait **502
Bad Gateway** en production (`/sante` répondait normalement — seul cet
outil était en cause). Cause confirmée : le modèle d'embeddings
(`paraphrase-multilingual-MiniLM-L12-v2`, chargé via `fastembed`) était
retéléchargé à chaque redémarrage de l'application (cache disque non
persistant, hors `data/etat/`) — même piège que celui déjà documenté pour
`corpus_index.json`, cette fois sur le modèle lui-même.

**Corrigé** : `cache_dir` de `fastembed.TextEmbedding` pointé vers
`data/etat/modeles/` (persistant, survit aux redéploiements). Vérifié en
production après déploiement : `rechercher_information` répond de nouveau
200 avec une vraie réponse. Outil réactivé dans le back-office.

**Point de vigilance mineur, sans rapport avec la panne** : sur le test de
validation ("Comment souscrire un abonnement ?"), la réponse retournée
("Dépositaires agréés") était d'une pertinence discutable — probablement
un sujet de calibrage des seuils/corpus plutôt qu'un bug, à surveiller à
l'usage sans urgence.

## Autre point non résolu ce soir (02/09)

Observé pendant les tests : le panneau "En ligne" côté ElevenLabs a affiché
un message d'accueil ("Bonjour. Que puis-je faire pour vous ?") qui ne
correspond pas du tout au "Premier message" configuré dans l'onglet Agent
(celui avec `{{outils_actifs}}`). Pas eu le temps d'investiguer — à vérifier
en premier à la reprise si possible : ce panneau teste peut-être une
version non publiée, ou un canal différent du widget "Widget"/téléphone
réel. Peut avoir faussé une partie des observations sur `{{outils_actifs}}`
ce soir (résultat vide) : à revérifier une fois ce point éclairci.

---

Ce document sert de point de reprise après une pause. Session très dense
(28/08) sur la satisfaction appelant, le créneau horaire, et une série de
bugs de production liés à `ELEVENLABS_API_KEY` — voir l'historique Git pour
le détail des commits. Session du 02/09 : personnalisation du message
d'accueil selon les outils actifs, dégradation gracieuse en cas d'échec
d'outil, et découverte de la panne ci-dessus.

## Où on en est

- **Pipeline vocal** : les 6 outils historiques + `enregistrer_satisfaction`
  fonctionnent, testés en conditions réelles (widget).
- **Déploiement Clever Cloud** : stable, déploiement automatique depuis
  GitHub (`main`) confirmé fonctionnel.
- **Back-office** : 3 onglets ("Live" / "Suivi" / "Prononciation"), fonctionnel.

## A. Expérience voyageur (voix)

- [x] **Horaires sur un créneau (14h-16h)** : nouveau `type=creneau` sur
      `horaires_theoriques`, avec `heure_debut`/`heure_fin` (HH:MM).
      Testé en conditions réelles (widget, ligne 9 / Pinechinade) : le
      modèle appelle bien l'outil avec les bons paramètres et la réponse
      est correcte. Au passage, corrigé un bug pré-existant qui faisait
      planter l'outil en 500 (au lieu d'un message d'erreur propre) dès
      qu'il rencontrait un cas d'erreur, y compris `arret_id` inconnu.
- [x] **5 nouvelles voix ajoutées** (`data/config.yaml`) : Clémence,
      Christian, Mélanie, David, Martin — écoutées et validées par
      l'équipe. Clémence jugée nettement plus fluide/naturelle qu'Hugo.
      Lucie/Hugo/Jade conservées pour l'instant (à retirer sur demande).
- [ ] **Balises audio ElevenLabs v3** (`[chaleureusement]`, `[avec
      empathie]`, `[avec patience]`) ajoutées au prompt et au premier
      message — proposées cette session, appliquées côté ElevenLabs par
      l'utilisateur. **À vérifier au prochain test** : le format exact des
      crochets n'a pas été confirmé en direct (accès ElevenLabs bloqué
      depuis cet environnement) — si le mot entre crochets est lu à voix
      haute littéralement, c'est que le format n'est pas reconnu.
      Important : ne fonctionne qu'avec des voix sur le modèle **v3**
      (Clémence l'est ; à vérifier pour les 4 autres nouvelles voix et
      pour Hugo/Lucie/Jade — les curseurs ton/style du back-office, eux,
      ne fonctionnent PAS sur les voix v3, seulement sur les modèles plus
      anciens).
- [ ] **Latence perçue** signalée comme un peu longue en test vocal — à
      objectiver au vrai test téléphonique (voir E).
- [ ] Continuer le cycle mesure-ajustement sur la prononciation au fil des
      tests — ce n'est jamais "terminé" (voir CLAUDE.md, pièges connus).
- [ ] **Discuter à qui revient la maintenance du dictionnaire de
      prononciation à terme** — l'outil d'édition existe côté back-office
      (onglet Prononciation).

## B. Expérience équipe (back-office)

### Fait cette session (28/08/2026)

- [x] **Satisfaction déclarée par l'appelant** — nouvel outil
      `enregistrer_satisfaction`, posé en fin d'appel ("est-ce que j'ai
      bien répondu à votre demande ?"), visible dans la tuile "Satisfaction
      client" (onglet Suivi) et dans une colonne dédiée du tableau des
      appels (👍/👎/—). **Confirmé fonctionnel de bout en bout sur un vrai
      appel** après plusieurs itérations :
      - 1er essai : le modèle posait la question mais n'appelait aucun
        outil (l'instruction ne le disait pas explicitement) — corrigé.
      - 2e essai : le modèle appelait le mauvais outil
        (`enregistrer_objet_perdu` au lieu de `enregistrer_satisfaction`),
        via une bascule automatique ElevenLabs vers GPT-4o suite à un
        raté du modèle principal (Gemini 2.5 Flash) — cause probable :
        descriptions d'outils trop proches ("Enregistre..." pour les
        deux). Description reformulée pour lever l'ambiguïté.
      - 3e essai : la question n'était pas posée du tout — fiabilité
        intrinsèque d'une consigne "juste avant de raccrocher" avec un
        LLM conversationnel, pas un bug corrigeable côté code. Prompt
        renforcé (consigne impérative, placée en fin de prompt) et
        déplacé en bas du prompt (effet de récence sur les longs prompts).
      - Une fausse déclaration d'objet perdu a été créée par le 2e raté
        ci-dessus — **à vérifier/nettoyer** dans l'export CSV objets
        perdus si toujours présente.
- [x] **Décalage horaire de -2h corrigé** sur tous les horodatages stockés
      en base (appels, évaluations, objets perdus, demandes de rappel,
      transferts, règles de prononciation, satisfaction) : le serveur
      Clever Cloud tourne en UTC, pas en heure française — même piège que
      celui déjà connu pour les horaires GTFS, jamais appliqué aux
      horodatages internes jusqu'ici. Nouvelle fonction `horodatage()`
      dans `assistant/outils/db.py`.
- [x] **Bug d'écoute/changement de voix en production — résolu.** Cause
      réelle, trouvée en plusieurs étapes : (1) `ELEVENLABS_API_KEY`
      totalement absente des variables d'environnement Clever Cloud
      (jamais transmise depuis le `.env` local, que Clever Cloud ne lit
      jamais) ; (2) une fois ajoutée, la clé notée était invalide (401
      ElevenLabs) — régénérée avec les permissions strictement
      nécessaires (Voix : Lire, ElevenAgents : Écrire). Au passage,
      l'erreur exacte est maintenant affichée directement dans le
      back-office (changement ET écoute de voix) au lieu d'un message
      générique — plus besoin des logs Clever Cloud, dont l'onglet s'est
      révélé peu fiable pour l'utilisateur (page vide sans explication,
      y compris en navigation privée) pour diagnostiquer ce genre de
      panne à l'avenir.
- [x] **Colonne "Satisfaction client"** ajoutée au tableau des appels
      (onglet Suivi), et tuile "Satisfaction client" distincte de la tuile
      "Évaluation équipe" (renommée pour éviter la confusion entre l'avis
      de l'appelant et celui de l'équipe).

### Restant / nouveau

- [ ] **⚠️ Nouveau, remonté par l'utilisateur (28/08)** : les interrupteurs
      "Outils actifs" du Live (Live) ne contrôlent que l'exécution
      backend (l'outil renvoie 503 si désactivé) — ils n'ont **aucun
      effet** sur ce que l'agent dit de ses propres capacités. Exemple
      concret : "Objet perdu" décoché, mais l'agent s'est quand même
      présenté en disant pouvoir "enregistrer un objet perdu". Cause :
      le premier message et le prompt système sont fixes côté ElevenLabs,
      complètement indépendants de notre état d'activation. Pas de
      correctif ce soir — plusieurs pistes possibles (message d'accueil
      plus générique pour ne rien promettre de précis ; variable
      dynamique injectée à l'initiation de l'appel pour refléter l'état
      réel ; consigne de dégradation gracieuse si un outil échoue) à
      discuter ensemble avant de choisir.
- [ ] **Le sélecteur de voix repart sur "Ne pas changer la voix" après un
      "Appliquer"** — comportement volontaire déjà documenté dans l'UI
      (la page ne réinterroge pas ElevenLabs pour rester rapide et
      indépendante), pas un bug. À changer seulement si ça gêne vraiment
      l'équipe à l'usage — impliquerait d'interroger ElevenLabs à chaque
      affichage de la page, comme "Appels en cours".
- [ ] **Vérifier la transcription sur un vrai appel** — déjà globalement
      confirmé fonctionnel via plusieurs charges JSON réelles collées
      cette session (rôles, tool_calls, tool_results tous lisibles), mais
      pas encore de vérification formelle dédiée.
- [ ] **Concurrence d'appels simultanés** — vérifié partiellement cette
      session : le plan actuel ("creator") autorise jusqu'à 10 appels
      simultanés (info obtenue par l'utilisateur). Reste à tester
      réellement 2-3 appels en parallèle pour confirmer que notre backend
      encaisse sans souci, avant le test live.
- [ ] **Synchroniser le dictionnaire de prononciation vers ElevenLabs** —
      toujours en attente de l'identifiant du dictionnaire côté ElevenLabs.
- [ ] **Numéro Twilio français** — en cours, mais **la certification
      réglementaire (Regulatory Compliance bundle) n'était pas terminée
      côté Twilio** à la fin de cette session, plus longue que prévu.
      À reprendre/recalibrer en premier la semaine prochaine avant de
      pouvoir relier le numéro et passer un vrai appel test.

## C. Dupliquer pour un autre réseau (pas commencé)

Inchangé depuis le 27/08 — voir version précédente de ce document dans
l'historique Git si besoin de détail. Toujours après B stabilisé et
sécurisé.

## D. Reporté à la fin du projet

- [ ] **Revue de sécurité complète**, notamment :
  - la vérification de la signature HMAC du webhook ElevenLabs (non
    vérifiée actuellement, décision explicite pour avancer plus vite) ;
  - le token `API_TOKEN` / mot de passe back-office a circulé en clair
    dans les échanges de cette session (nécessaire pour diagnostiquer les
    pannes de production sans accès aux logs) — à régénérer avant mise en
    production réelle avec de vrais appelants.
- [ ] **Horaires d'ouverture réels du CRC** — remonté par l'utilisateur
      (02/09) : le prompt distingue déjà "CRC ouvert" / "CRC fermé" (section
      "Sorties", transfert vs rappel), mais rien ne précise aujourd'hui les
      vraies plages horaires d'ouverture. À préciser au moment du lancement
      réel du service, pas avant — la formule actuelle du prompt convient
      pour l'instant selon l'utilisateur.

## E. Protocole de test téléphonique réel (après le numéro Twilio français)

Toujours en attente du numéro Twilio français (voir B). Une fois le numéro
actif : scénarios d'appel (chaque outil au moins une fois, y compris un cas
d'erreur/hors périmètre et le nouveau créneau horaire), points de mesure
(latence perçue, prononciation, transfert humain, question de satisfaction),
grille de recueil des résultats — probablement dans le back-office
(évaluation par appel, déjà existante).

## Suggestion pour la reprise (semaine prochaine)

1. **Recalibrer/finaliser le bundle réglementaire Twilio France** — bloquant
   pour tout le reste de cette liste.
2. Une fois le numéro actif : **relier le numéro à l'agent ElevenLabs**
   (même mécanisme que le numéro US), puis **vrai test téléphonique** (E).
3. **Discuter la cohérence "outils désactivés" / "ce que dit l'agent"**
   (nouveau point B ci-dessus) — choisir une approche avant qu'elle ne
   cause une vraie confusion en situation réelle.
4. Vérifier la concurrence d'appels simultanés réellement (2-3 appels en
   parallèle), avant le test live.
5. Nettoyer la fausse déclaration d'objet perdu créée par le bug de
   satisfaction (si toujours présente).
6. Vérifier le format des balises audio `[chaleureusement]` etc. sur un
   vrai appel avec Clémence.
