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

## Redécoupage des catégories du Live (proposition du 02/09, à valider)

Un collègue de l'utilisateur a partagé la grille de classification réelle
des demandes CRC : **Objets perdus, Horaires, Commercial, Vélo en libre
service, Transport à la demande, Amendes** (un 7e élément "%" dans le
message d'origine était une erreur de copie, pas une vraie catégorie).

Le vrai décalage : "Horaires" et "Objets perdus" correspondent déjà
chacun à un outil/interrupteur dédié, mais "Commercial", "Vélo en libre
service", "Transport à la demande" et "Amendes" sont **tous fondus dans un
seul interrupteur** aujourd'hui ("Questions tarifs / pratique FAQ" =
l'outil `rechercher_information`). Bonne nouvelle : cet outil a déjà une
catégorisation interne plus fine (héritée du contenu scrapé du site) qui
correspond bien :

| Catégorie CRC | Catégorie technique existante |
|---|---|
| Horaires | `horaires_theoriques` (outil séparé, inchangé) |
| Objets perdus | `enregistrer_objet_perdu` (outil séparé, inchangé) |
| Commercial | `rechercher_information` / catégorie `tarifs` (+ `agences` ?) |
| Vélo en libre service | `rechercher_information` / catégorie `vls` |
| Transport à la demande | `rechercher_information` / catégorie `tad` |
| Amendes | `rechercher_information` / catégorie `procedures` (la page "amendes" du site y est déjà classée) |

**À trancher avec l'utilisateur** : les catégories `conditions` (CGU,
conseils de voyage...) et `accessibilite` n'ont pas de correspondance
évidente dans la liste CRC — les rattacher à "Commercial" par défaut, ou
en faire une 7e case à part ?

**Implication technique (pas un simple renommage)** : aujourd'hui
l'activation se fait par outil (une ligne en base par outil, vérifiée
avant même de lire le corps de la requête). Découper `rechercher_information`
par catégorie demanderait que la vérification d'activation regarde la
catégorie demandée dans chaque appel — touche la base de données, le code
d'activation (`assistant/backoffice/activation.py`), et l'écran Live. Un
vrai chantier, pas fait avant validation du découpage final avec l'utilisateur.

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

## Suggestion pour la reprise (03/09, priorités explicites de l'utilisateur)

1. **Twilio France** — reprendre où la certification réglementaire en est
   (relancée en fin de session du 02/09, "under review").
2. **Ajustement du message d'accueil** — élucider d'abord l'incohérence du
   panneau "En ligne" ElevenLabs (voir point ouvert plus haut) avant de
   conclure quoi que ce soit sur `{{outils_actifs}}` ; refaire le test
   proprement une fois ce point éclairci.
3. **Valider le redécoupage des catégories du Live** avec l'utilisateur
   (proposition détaillée ci-dessus) avant de commencer l'implémentation.
4. **Cadrer le routage téléphonique / horaires CRC / débordement** (section
   F ci-dessus) — potentiellement le sujet le plus structurant pour rendre
   ce POC testable par l'équipe.

Autres points en attente, moins prioritaires que les 3 ci-dessus :
- Une fois le numéro Twilio actif : relier le numéro à l'agent ElevenLabs,
  puis vrai test téléphonique (E).
- Vérifier la concurrence d'appels simultanés réellement (2-3 appels en
  parallèle), avant le test live.
- Nettoyer la fausse déclaration d'objet perdu créée par le bug de
  satisfaction (si toujours présente).
- Vérifier le format des balises audio `[chaleureusement]` etc. sur un
  vrai appel avec Clémence.
