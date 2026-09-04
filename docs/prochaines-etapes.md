# Prochaines étapes — état au 04/09/2026 (fin de session)

## ⚠️ Action bloquante avant toute chose : commiter le nouvel index

`data/corpus_index.json` a été régénéré dans ta session Codespaces (suite au
nettoyage du pied de page, voir plus bas) mais **n'est pas encore commité** —
je n'ai pas ce fichier de mon côté, seulement toi. Depuis Codespaces :

```bash
git add data/corpus_index.json
git commit -m "Regenere l'index apres le nettoyage du widget acces rapide (04/09)"
git push origin main
```

Tant que ce n'est pas fait, la production tourne encore sur l'ancien index
(sans le nettoyage du pied de page ni le synonyme "abonnement" à jour).

## ✅ Fait le 04/09 (après-midi/soir) — pollution du corpus et exploration modèle

**Deux vrais bugs de contenu trouvés et corrigés** (voir aussi la section
"itération sur le véto lexical" juste en dessous pour la partie seuils/code) :

1. **Synonyme "abonnement" manquant** : le mécanisme existait déjà dans
   `extraire_tarifs.py` (`PASS MENSUEL/ANNUEL` → "abonnement") mais l'index
   commité n'avait jamais été régénéré depuis son ajout. Corrigé par un
   rafraîchissement complet. "Je voudrais prendre un abonnement, comment je
   fais ?" passe de `trouve=False` à une réponse correcte.
2. **Widget "accès rapide" du site scrapé dans chaque page** : un bloc de
   liens (Itinéraire, Horaires, TAD, Paiement des amendes...) identique en
   bas de chaque page, sans conteneur dédié à exclure. Corrigé
   (`assistant/ingestion/extraire_corpus.py`, sélecteur `a.btn-quick-access`
   ajouté à `SELECTEURS_BRUIT`). Diluait `amendes.md` et faisait gagner à
   tort `faq.md` sur des questions amendes (le lien contenait littéralement
   le mot "amendes").

**Reste ouvert malgré ce nettoyage** (vérifié après rafraîchissement complet,
77 blocs réindexés) :
- `amendes.md` perd toujours face à `faq.md` sur "Comment payer une amende ?"
  et 2 questions voisines — cette fois pour une raison différente : le bloc
  FAQ "Comment payer et valider avec ma carte bleue ?" partage la tournure
  exacte "Comment payer..." avec la question, alors qu'`amendes.md` dit
  "réglant votre amende" / "solutions de paiement" (jamais le mot "payer").
  Les deux blocs ne partagent donc qu'1 mot chacun avec la question — c'est
  le score sémantique qui tranche, et le modèle actuel se laisse guider par
  la ressemblance de tournure plus que par le vrai sujet. **Limite du modèle
  d'embeddings, pas un bug de contenu ou de seuil.**
- Dépositaires-agréés, courrier/nous-contacter, tad-coûte, Rognac : toujours
  en échec, même mécanisme (un document voisin mais faux gagne en position 1
  et passe le véto lexical avec 1 seul mot commun).
- Recul sur les questions pièges (1/8 correct, contre 2/8 avant le 03/09) :
  effet de bord confirmé du correctif "regarder les 5 meilleurs candidats" —
  plus on regarde de candidats, plus une question piège a de chances qu'un
  candidat partage un mot par coïncidence. Non traité.

**Exploration model — jauge d'impact, puis mesures réelles.** Le budget
CLAUDE.md (300 ms/endpoint) n'est pas le facteur limitant (marge de 10 à 25x
avec le modèle actuel) : c'est le **déploiement Clever Cloud** qui l'est —
e5-large (2,25 Go) avait déjà fait échouer 3 déploiements de suite (mémoire,
quota CPU, disque) lors d'un essai précédent.

Trois modèles mesurés en local (RAM et latence réelles, pas des specs
papier) :

| Modèle | RAM mesurée | Latence (régime de croisière) | Palier Clever Cloud nécessaire |
|---|---|---|---|
| `paraphrase-multilingual-MiniLM-L12-v2` (actuel) | 654 Mo | 10 ms | 1 Go, ~16€/mois (déjà en place) |
| `paraphrase-multilingual-mpnet-base-v2` | 1915 Mo | 37 ms | Non viable même à 2 Go (32€/mois) ; sans doute 4 Go (76€/mois) |
| `antoinelouis/biencoder-distilcamembert-mmarcoFR` (français uniquement, PyTorch) | 993 Mo | 43-60 ms (258 ms au 1er appel, effet de démarrage à froid) | Non viable à 1 Go ; probablement 2 Go (32€/mois), avec une marge correcte cette fois |

Le candidat français (distillation de CamemBERT, entraîné spécifiquement
pour la recherche documentaire) est le meilleur compromis technique trouvé —
mais (a) implique soit d'ajouter PyTorch comme dépendance permanente du
projet (lourd), soit une conversion ONNX (travail d'ingénierie non fait),
et (b) sa qualité réelle sur nos questions n'a **pas été testée** (seuls le
poids et la vitesse ont été mesurés) — demanderait de réindexer tout le
corpus avec ce modèle et de relancer `evalcorpus` pour le savoir.

**Décision** : mise en pause volontaire, aucun engagement budgétaire pris.
Utilisateur : "pour l'heure, je ne veux pas m'engager sur ces montants."
On reste sur le modèle actuel (patché au fil de l'eau) en attendant une
décision, potentiellement après le test de qualité du candidat français.

**Idées soulevées par l'utilisateur, à creuser, pas actionnées :**
- Trouver une méthode pour identifier systématiquement ce qui est "assez
  critique" pour mériter un patch ciblé, si on reste sur le modèle actuel
  patché indéfiniment (plutôt que de continuer au coup par coup comme
  aujourd'hui).
- Demander à des collègues de la filiale une base documentaire séparée sur
  des sujets qui évoluent peu (les amendes, par exemple) — s'émanciper du
  site web public comme unique source, qui n'est pas forcément écrit pour
  être une base de connaissance interrogeable.

## Prochaines étapes — reprise de lundi

1. **Vérifier que `data/corpus_index.json` a bien été commité** (action
   bloquante ci-dessus) et confirmer via `evalcorpus` que la prod reflète
   bien le nettoyage du pied de page + le synonyme abonnement.
2. **Twilio** : vérifier l'avancement de la certification réglementaire —
   l'utilisateur a bon espoir que ça ait avancé. Si débloqué : relier le
   numéro à l'agent ElevenLabs, vérifier `{{outils_actifs}}` sur un vrai
   appel, protocole de test téléphonique complet (section E du suivi).
3. **Décider de la suite sur le modèle d'embeddings** : soit on lance le
   test de qualité du candidat français (réindexer + evalcorpus), soit on
   assume le modèle actuel "patché" et on passe au point 4.
4. **Si on reste sur le modèle actuel patché** : définir une méthode pour
   trancher rapidement "ce cas mérite-t-il un patch ciblé ou pas" — éviter
   de refaire une session de plusieurs heures par cas isolé remonté.
5. **Piste base documentaire alternative** : évaluer avec l'utilisateur si
   demander une base structurée aux collègues de la filiale (sujets stables
   comme les amendes) est réaliste, et ce que ça changerait dans le pipeline
   d'ingestion.
6. **Bilan de la semaine face à l'objectif initial** : où en est le projet,
   qu'est-ce qui a été appris, qu'est-ce qui reste flou.
7. **Duplication sur un autre réseau de transport** : quelles questions se
   poser avant de s'y engager (voir aussi section C du suivi, jamais
   commencée).
8. **Back-office à remettre aux collègues** : être au clair sur ce qui est
   prêt à être pris en main par l'équipe CRC vs ce qui reste piloté par
   l'utilisateur seul.
9. **Échéance concrete la plus proche : démo aux collègues directs** pour un
   premier retour bienveillant. Deux conditions posées par l'utilisateur :
   (1) l'expérience d'appel doit être très bonne, (2) les collègues doivent
   pouvoir se projeter facilement dans l'usage du back-office (le prendre en
   main eux-mêmes, ou au moins en parler avec aisance). À traduire en
   checklist concrète avant la démo — scénarios d'appel à tester, parcours
   back-office à répéter, points de friction à éliminer en priorité.

---

## ✅ Fait le 04/09 — itération sur le véto lexical, une régression détectée et annulée

Suite directe du point du 03/09 ci-dessous. Deux choses à retenir pour la
méthode de travail avant le détail technique :

- **Push automatique côté Claude, pull manuel côté toi** : chaque commit
  que je fais est poussé immédiatement sur GitHub. Mais ton terminal
  Codespaces est une copie locale indépendante qui ne se met à jour que
  sur `git pull origin main` explicite — rien d'automatique comme sur
  Clever Cloud (qui a un webhook GitHub configuré pour se redéployer
  seul). Premier run d'evalcorpus du 04/09 fait sans pull préalable :
  résultats identiques au run de la veille, ce qui a permis de repérer le
  problème avant de mal interpréter des chiffres obsolètes.

- **Piste testée et abandonnée le jour même** : exiger 2 mots
  significatifs partagés (au lieu d'1 seul) pour accepter un candidat,
  dans l'idée de réduire les faux positifs en position 1 (voir point du
  03/09). Résultat mesuré après déploiement : **69% au lieu de 80%** — net
  recul, malgré une légère amélioration sur les pièges (4/8 au lieu de
  2/8). Cause : sur une question courte à 2 mots significatifs dont un
  mot interrogatif ("C'est combien un ticket ?" → "combien", "ticket"),
  "combien" ne peut structurellement jamais apparaître dans un texte de
  réponse — exiger 2 mots revient à rejeter systématiquement ce genre de
  question. Cassé au passage : "vélo ?", "chien ?", désinscription SMS,
  entre autres questions auparavant correctes. **Annulé, retour à 1 mot
  minimum.**

- **Correctif conservé, indépendant de la régression ci-dessus** : le
  `break` sur `SEUIL_BASSE` (score sémantique trop bas) remplacé par un
  `continue`, pour que le bon document puisse être trouvé même en 3e
  position avec un score déjà sous ce seuil (cas "abonnement" du 03/09).
  Pas encore confirmé sur un run propre (le run avec le seuil à 2 mots
  masquait son effet sur ce cas précis) — **à revérifier au prochain
  evalcorpus**.

- **⚠️ Nouvelle observation, non expliquée** : entre deux runs d'evalcorpus
  utilisant exactement le même corpus et modèle (aucun changement de code
  qui les concerne), le rappel top-5 est passé de 100% à 94% et les
  scores sur les questions "amendes" ont changé (ex. "Comment payer une
  amende ?" : `amendes.md` premier avec score 1.000 sur un run, absent du
  top-5 avec score 0.997 sur `faq.md` à sa place sur l'autre run). Piste
  la plus probable : le modèle d'embeddings est retéléchargé à chaque run
  dans cet environnement Codespaces (`data/etat/` n'y persiste pas comme
  sur Clever Cloud), et son identifiant Hugging Face
  (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`) n'est
  pas figé sur une révision précise — si le dépôt HF est mis à jour entre
  deux téléchargements, les vecteurs de `corpus_index.json` (calculés une
  fois, figés) et les vecteurs de question (calculés à la volée) peuvent
  ne plus venir exactement du même modèle. À vérifier avant de tirer une
  conclusion (pourrait aussi être un phénomène plus anodin) — **pas
  traité, priorité à discuter avec l'utilisateur** : c'est un sujet de
  fond (reproductibilité, "Vérifiabilité" au sens de CLAUDE.md), pas
  urgent au jour le jour puisque Clever Cloud garde son propre modèle en
  cache une fois téléchargé.

**Prochaine étape immédiate** : repull + relancer `assistant.evalcorpus`
pour confirmer qu'on est bien revenu à la base (80%, rappel 100%, pièges
2/8) et que le cas "abonnement" est cette fois résolu proprement par le
`continue` seul.

## ✅ Fait le 03/09 (soir) — première évaluation réelle du corpus (`assistant.evalcorpus`)

Remonté par l'utilisateur : deux questions simples et légitimes sur les
tarifs ("abonnement", "prix d'un trajet") n'obtenaient aucune réponse en
conditions réelles, alors que le bouton Commercial était bien actif.
Diagnostiqué en faisant tourner `uv run python3 -m assistant.evalcorpus`
(54 questions, dont 8 pièges) depuis un terminal avec accès réseau (cet
environnement ne peut pas atteindre Hugging Face).

**Résultat avant correctif** : rappel top-5 100% (54/54 — le bon bloc
est toujours dans les 5 premiers candidats), mais réponse outil
seulement 80% (43/54). L'écart venait presque entièrement d'un même
défaut : `rechercher_information` ne regardait que le tout premier
candidat ; si celui-ci échouait le véto lexical (aucun mot en commun
avec la question), la réponse était `trouve=False` même quand un
candidat suivant, tout aussi bien classé, aurait répondu correctement.

**Corrigé** : la fonction regarde maintenant les 5 meilleurs candidats
dans l'ordre et renvoie le premier qui passe les deux vérifications
(score + véto lexical), au lieu d'abandonner au premier échec. Changement
isolé, sans effet sur la détection des questions pièges. Vérifié
localement sans régression (`verifier_backoffice.py` 12/12,
`verifier_api.py` 7/8 — seul échec restant : le test réseau bloqué dans
ce sandbox, déjà connu). **Poussé sur `main`, déployé.**

**⚠️ Point sérieux découvert au passage, PAS encore traité** : sur les 8
questions pièges de l'évaluation, 6 ont reçu une réponse alors qu'elles
auraient dû obtenir `trouve=False` — dont 2 avec une confiance "haute"
(par exemple une question demandant le numéro de téléphone d'un autre
opérateur, SNCF, à laquelle l'outil a répondu en utilisant le contenu de
la page "Nous contacter" de ce réseau-ci). Remonter les seuils ne suffira
probablement pas à lui seul : plusieurs pièges obtiennent un score aussi
élevé, voire plus élevé, que de vraies questions légitimes — la
distribution des scores se chevauche. À traiter par expérimentation
itérative (ajustement seuils/véto lexical + relance d'`evalcorpus` par
l'utilisateur à chaque essai), pas par un simple changement de constante.

**Prochaine étape immédiate** : demander à l'utilisateur de relancer
`uv run python3 -m assistant.evalcorpus` une fois ce correctif déployé,
pour confirmer que les questions tarifs qui échouaient sont bien
résolues et qu'aucune régression n'apparaît sur les pièges — avant de
s'attaquer au point ⚠️ ci-dessus.

**Aussi demandé le même soir, pas encore traité** : clôture d'appel plus
chaleureuse — le "au revoir" final est actuellement un peu brut. Piste
proposée : *"Après avoir remercié l'appelant pour son retour, termine
toujours par une formule de clôture chaleureuse avant de raccrocher (par
exemple 'Merci de votre appel, bonne journée !'), plutôt qu'un simple
accusé de réception suivi d'un silence en attendant que l'appelant dise
au revoir."* — à ajouter au prompt ElevenLabs (à faire par l'utilisateur
côté ElevenLabs, comme les autres consignes de prompt) et à confirmer
appliqué.

## ✅ Résolu — rechercher_information (502 en production, 02/09)

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
        ci-dessus — **nettoyée le 03/09** (nouvelle route de suppression
        `assistant/backoffice/exports.py::supprimer_objet_perdu`, testée,
        puis utilisée pour retirer la ligne concernée en production).
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

### Fait le 02/09/2026

- [x] **Cohérence "outils désactivés" / discours de l'agent** — remontée le
      28/08. Deux volets traités :
      - **Dégradation gracieuse (C)** : consigne ajoutée au prompt — si un
        outil échoue, l'agent s'excuse et propose systématiquement un
        transfert/rappel plutôt que d'inventer une réponse ou d'échouer
        sec. **Testée et confirmée fonctionnelle** via le widget.
      - **Message d'accueil reflétant l'état réel (B)** : nouveau webhook
        `/webhooks/elevenlabs/personnalisation`, appelé par ElevenLabs
        avant le début d'un appel Twilio/SIP/WhatsApp (pas le widget),
        fournit la variable `{{outils_actifs}}` insérée dans le premier
        message. Backend testé et fonctionnel (curl direct). **Pas encore
        vérifié en conditions réelles** — voir point ouvert juste en
        dessous, le panneau de test utilisé n'affichait pas le bon
        message d'accueil, faussant potentiellement l'observation.
- [x] **rechercher_information (502 en production)** — voir section tout en
      haut de ce document, résolu et vérifié.
- [x] **5 voix ajoutées**, **créneau horaire**, **décalage horaire** — voir
      section A et le haut de ce document.

### Restant / nouveau

- [ ] **⚠️ Nouveau (02/09)** : proposition de redécoupage des catégories
      du Live, à valider avec l'utilisateur avant implémentation — voir
      section dédiée ci-dessous ("Redécoupage des catégories du Live").
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

## ✅ Fait le 03/09 — Redécoupage des catégories du Live

Grille de classification réelle du CRC (partagée par un collègue de
l'utilisateur) : **Objets perdus, Horaires, Commercial, Vélo en libre
service, Transport à la demande, Amendes**. "Horaires" et "Objets perdus"
avaient déjà chacun un interrupteur dédié ; les 4 autres étaient fondus
dans un seul interrupteur ("Questions tarifs / pratique FAQ" =
`rechercher_information`).

**Implémenté** : 4 interrupteurs distincts pour `rechercher_information`
(Commercial, Vélo en libre service, Transport à la demande, Amendes),
alignés sur sa catégorisation interne déjà existante. `conditions` et
`accessibilite` rangés dans "Commercial" (décision utilisateur).

Découverte en creusant : la catégorie technique `procedures` mélangeait
la page "Amendes" du site ET la FAQ générale — isolée en une catégorie
`amendes` à part (2 blocs reclassés dans `corpus_index.json`,
`extraire_corpus.py` mis à jour) pour que couper les amendes ne coupe pas
la FAQ générale au passage.

Double filtrage pour ne jamais laisser fuiter un sujet coupé : 503 propre
si la catégorie précisée par le modèle est désactivée, et exclusion
silencieuse des catégories désactivées de la recherche même quand la
catégorie n'est pas précisée. Testé et vérifié localement (503 sur
catégorie désactivée, filtrage confirmé) — **pas encore testé sur un vrai
appel** (nécessite le modèle d'embeddings, réseau bloqué depuis cet
environnement).

**Ajustements suite à la relecture de l'utilisateur (même jour)** :
- **"Identifier un arrêt" fusionné dans "Horaires"** — un interrupteur
  séparé permettait la combinaison cassée "horaires actif, mais recherche
  d'arrêt coupée" (horaires en dépend directement). La grille passe de 9
  à 6 cases : Horaires, Commercial, Vélo en libre service, Transport à la
  demande, Amendes, Déclarer un objet perdu.
- **"Demander à être rappelé" et "Transférer vers un conseiller" ne sont
  plus désactivables du tout** — ce sont les deux seules portes de sortie
  vers un humain ; les laisser désactivables risquait de laisser un
  appelant sans aucun recours, contraire au principe fondateur du projet.
  Retirées de la grille et du mécanisme d'activation en base.

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

## F. Routage téléphonique / horaires CRC / débordement (nouveau, 02/09)

Sujet neuf, pas encore scopé. Tout ce qui existe suppose que 100% des
appels arrivant sur le numéro Twilio parlent au bot, le transfert humain
étant une décision prise *pendant* la conversation (déjà en place). Ce que
l'utilisateur envisage pour la mise à disposition à ses collègues est
différent : un aiguillage *avant* que le bot décroche (hors horaires CRC,
et/ou en débordement si les lignes humaines sont occupées).

Probablement pas qu'une question Twilio — dépend de l'infrastructure
téléphonique existante du CRC. Questions à répondre ensemble avant de
proposer une architecture :
1. Aujourd'hui, comment un appel arrive-t-il à un agent CRC (standard
   existant, logiciel de centre d'appels, postes directs) ?
2. Mode souhaité : bot hors horaires uniquement, bot en débordement
   uniquement, ou les deux ?
3. Le débordement nécessite de savoir si les agents humains sont occupés
   — probablement une intégration avec le système d'appels existant du
   CRC, pas seulement une configuration Twilio.

Potentiellement le sujet le plus structurant de tous ceux en attente,
puisqu'il conditionne comment ce POC devient testable par l'équipe CRC à
petite échelle (MVP).

## E. Protocole de test téléphonique réel (après le numéro Twilio français)

Toujours en attente du numéro Twilio français (voir B). Une fois le numéro
actif : scénarios d'appel (chaque outil au moins une fois, y compris un cas
d'erreur/hors périmètre et le nouveau créneau horaire), points de mesure
(latence perçue, prononciation, transfert humain, question de satisfaction),
grille de recueil des résultats — probablement dans le back-office
(évaluation par appel, déjà existante).

## Suggestion pour la reprise (03/09 soir, priorités explicites de l'utilisateur)

1. **Relancer `assistant.evalcorpus`** après déploiement du correctif
   rechercher_information, pour confirmer que les questions tarifs
   échouées sont résolues et qu'il n'y a pas de régression sur les pièges.
2. **⚠️ Questions pièges répondues à tort** (6/8, dont 2 en confiance
   "haute") — le sujet le plus sérieux en attente côté fiabilité, à
   traiter par expérimentation itérative de seuils avec `evalcorpus`
   comme instrument de mesure.
3. **Confirmer la clôture d'appel plus chaleureuse** — texte de consigne
   déjà proposé (voir section du soir ci-dessus), à appliquer côté
   ElevenLabs et à valider en test.
4. **Twilio France** — appel passé côté utilisateur le 03/09 pour
   débloquer la certification réglementaire ; à vérifier où ça en est.
5. **Cadrer le routage téléphonique / horaires CRC / débordement** (section
   F ci-dessus) — potentiellement le sujet le plus structurant pour rendre
   ce POC testable par l'équipe.

Autres points en attente, moins prioritaires que les 5 ci-dessus :
- Une fois le numéro Twilio actif : relier le numéro à l'agent ElevenLabs,
  puis vrai test téléphonique (E), y compris vérification de
  `{{outils_actifs}}` sur un vrai appel (webhook de personnalisation,
  backend déjà testé et fonctionnel, jamais confirmé sur appel réel).
- Vérifier la concurrence d'appels simultanés réellement (2-3 appels en
  parallèle), avant le test live.
- Vérifier le format des balises audio `[chaleureusement]` etc. sur un
  vrai appel avec Clémence.
- Décider si la sélection de tonalité par tags (plutôt que les curseurs
  ton/style actuels) mérite d'être construite — discuté et validé
  conceptuellement le 03/09, explicitement pas actionné pour l'instant.
