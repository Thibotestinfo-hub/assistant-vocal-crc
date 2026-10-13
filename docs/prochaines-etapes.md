# Prochaines étapes — état au 25/09/2026

## ✅ Fait le 13/10/2026 — formule d'accueil du SMS réintégrée

Correction immédiate après le chantier précédent : la formule d'accueil
personnalisée ("Bonjour {nom}, voici votre itinéraire sur le réseau
TABM") avait été retirée en calquant trop littéralement la maquette
(qui ne la montrait pas dans la capture partagée — probablement un
rognage de l'aperçu, pas une absence voulue). L'utilisateur confirme la
vouloir : "c'est important de tisser un lien avec le voyageur". Remise
en place dans `_formater_sms_emoji`/`_formater_sms_texte`
(`assistant/outils/sms.py`), en première ligne avant l'en-tête
"Arrivée à...". Repli générique ("Voici votre itinéraire...") si
l'appelant n'a pas donné son prénom/nom. Le lien Google Maps n'avait
lui jamais été touché, vérifié au passage qu'il reste bien présent.

Vérifié en local : rendu avec et sans nom, version texte confirmée
100% ASCII (nom passé dans `_sans_accents` comme le reste des données
dynamiques). `verifier_api.py` (7/8, échec sandbox connu) et
`verifier_backoffice.py` (12/12) sans régression.

## ✅ Fait le 13/10/2026 — format du SMS refait à partir de la vraie maquette

Suite du point 5 des REX ci-dessous : l'utilisateur a repartagé l'image
de la maquette ("Assistant TABM"), jamais vue directement jusqu'ici
(reconstruite plus tôt dans la session à partir d'une description texte
dans un résumé de conversation). Comparaison précise faite, plusieurs
écarts trouvés et corrigés dans `assistant/outils/sms.py` :

- **En-tête** : "Arrivée à [DESTINATION] : HH:MM" en première ligne,
  puis "durée · N bus · N changements" (et non plus un titre
  "Bonjour..." qui n'existe pas dans la maquette — personnalisation
  retirée du texte du SMS, le prénom/nom reste utilisé ailleurs pour le
  suivi back-office).
- **Durée totale** : "1 h 09" au-delà d'une heure plutôt que "69 min"
  (nouveau `_duree_libelle`).
- **Marche initiale** : heure réelle de départ à pied affichée
  ("Départ 15:10 · 3 min à pied"), calculée à rebours depuis l'heure du
  premier bus moins la durée de marche — nouveau calcul
  (`heure_depart_reelle`), jamais affiché si l'un des deux manque.
- **Temps d'attente** : repositionné à la fin du bloc du trajet qui
  précède (juste après "Descendre..."), pas au début du suivant comme
  dans la version précédente — même donnée, autre emplacement, pour
  coller à la maquette.
- **Numérotation** : seuls les trajets en bus sont numérotés (1, 2, 3),
  les étapes de marche ne le sont pas — la version précédente numérotait
  tout, y compris les marches.
- **"Horaires à jour à HH:MM"** : ajouté en pied de SMS, calculé au
  moment de la construction du texte (jamais une valeur statique ou
  devinée).
- **Version texte (GSM-7)** : en retirant les accents des textes qu'on
  écrit nous-mêmes, un bug est apparu — les noms d'arrêts réels
  ("Plantée", "Émile Ripert") contiennent eux aussi des accents, donc
  un seul d'entre eux suffisait à faire basculer tout le SMS en UCS-2
  malgré le format "texte" choisi. Nouveau `_sans_accents()` appliqué
  à toutes les données dynamiques (nom d'arrêt, ligne, direction),
  vérifié par un test explicite (SMS généré 100% ASCII).

Vérifié en local : rendu emoji comparé ligne à ligne à la maquette sur
les données exactes de l'exemple (Emile Ripert → Sainte Anne, 3 bus) —
correspondance confirmée. Cas limites testés (1 seul bus sans
changement, données manquantes — jamais de valeur fabriquée, juste
l'absence de la ligne concernée). Segments SMS recalculés sur l'exemple
réel : 7 segments en emoji contre 3 en texte, cohérent avec l'écart
déjà mesuré. `verifier_api.py` (7/8, échec sandbox connu) et
`verifier_backoffice.py` (12/12) sans régression.

## ✅ Fait le 13/10/2026 — 5 REX d'un nouveau test réel, analysés via webhook

Test complet après republication du prompt corrigé. 5 retours, chacun
vérifié sur le webhook réel plutôt que supposé :

**1. Tarification simple non testée** — oubli de l'utilisateur, rien à
corriger.

**2. "~10s sur l'API Google" — pas Google en cause.** Vérifié précisément
sur les timestamps du webhook : `calculer_itineraire_complexe` a répondu
en 1,1s (rapide). Le vrai délai (32s puis 14s) se situe entre le moment
où l'agent annonce qu'il va vérifier et le moment où il appelle
réellement l'outil — deux `user_turn_timeout` déclenchés entre-temps,
avec des relances automatiques ("Je suis toujours là..."). Cause
probable : variabilité de réponse du LLM sous-jacent (Gemini 3.1 Flash
Lite) à déclencher l'appel d'outil, même catégorie que le repli vers un
modèle de secours déjà observé dans un appel précédent. Pas de
correction de code possible de notre côté — comportement du fournisseur
LLM, pas de notre pipeline.

**3. SMS envoyé sans confirmation du numéro — bug confirmé.** Le webhook
montre `envoyer_sms_itineraire` appelé immédiatement après avoir entendu
le numéro, sans jamais le répéter ni attendre de confirmation — la
"confirmation" prononcée par l'agent arrivait après l'envoi, pas avant,
en violation de la règle déjà écrite. Corrigé : la règle impose
maintenant explicitement deux tours de parole séparés (même schéma que
la satisfaction, qui tient mieux) — répéter le numéro et demander
confirmation dans un tour, appeler l'outil seulement au tour suivant si
confirmation reçue.

**4. Satisfaction enregistrée sans attendre — bug confirmé, récidive.**
Le webhook montre `enregistrer_satisfaction(satisfait=true)` appelé
sans aucun nouveau tour de parole après la question — l'agent a réutilisé
une phrase de l'appelante ("c'est parfait, merci beaucoup") qui
répondait en réalité à la question précédente ("avez-vous besoin
d'autre chose ?"), pas à la question de satisfaction posée juste après.
Exactement le cas que la règle existante (déjà présente, déjà corrigée
une première fois le 28/09/2026) est censée empêcher. Renforcée avec
une phrase ciblant précisément cette confusion : une réponse antérieure
à la question ne compte jamais, même si elle semblait positive.

**5. SMS pas conforme à la maquette partagée, "horaires à jour" absent**
— en cours, pas encore corrigé. Le format SMS construit plus tôt dans
cette session (`assistant/outils/sms.py`) a été conçu à partir d'une
**description texte** de la maquette (reçue dans un résumé de
conversation), jamais de l'image elle-même. Possible que des éléments
aient été mal reconstruits ou oubliés (le "horaires à jour" mentionné
par l'utilisateur n'apparaît dans aucune note de cette session). Demande
faite à l'utilisateur de repartager l'image pour comparer précisément
plutôt que deviner une 2e fois.

**Fichier modifié** : `docs/spec-assistant-vocal-v0-revisee.md`, §5
(règle SMS/numéro de téléphone, règle satisfaction). **Pas encore collé
côté ElevenLabs** — à faire par l'utilisateur, comme toujours.

## ✅ Fait le 13/10/2026 — latence de ~10s sur rechercher_information, trouvée et corrigée

Suite directe du test téléphonique réel : un webhook montrait
`tool_latency_secs: 10.000244387891144` sur un appel à
`rechercher_information`, très loin du budget de 300 ms de CLAUDE.md,
en pleine conversation. Coïncide avec l'échec récurrent du même outil
dans `verifier_api.py` tout au long de cette session, toujours écarté
comme "souci réseau du bac à sable" sans être creusé — à tort.

**Cause racine, en deux temps** :
1. `_charger_modele()`/`_charger_index()` (`assistant/outils/
   rechercher_information.py`) sont des caches paresseux (globals
   chargés au premier appel). Rien ne les préchargeait au démarrage de
   l'application : c'est le premier appelant réel après un déploiement
   ou un redémarrage qui payait ce coût, en pleine conversation.
2. Plus profond : même avec le modèle déjà en cache sur disque
   (`data/etat/modeles/`), `fastembed` contacte Hugging Face par défaut
   pour vérifier la révision du dépôt avant d'utiliser ce cache — un
   appel réseau, pas juste une lecture disque. Le correctif du
   02/09/2026 (mise en cache pour éviter de retélécharger le modèle)
   n'empêchait pas cette vérification en ligne à chaque démarrage, un
   coût distinct resté non corrigé jusqu'ici.

**Implémenté** :
- `TextEmbedding(..., local_files_only=True)` en premier essai
  (`_charger_modele`), avec repli sur l'ancien comportement (accès
  réseau) uniquement si le cache est encore vide (tout premier
  démarrage sur un environnement neuf). Règle au passage un risque de
  reproductibilité déjà identifié dans ce fichier (une révision de
  modèle qui changerait silencieusement entre le calcul de l'index et
  une requête en direct) : on utilise désormais toujours la version
  déjà en cache, jamais une plus récente récupérée à la volée.
- `prechauffer()`, nouvelle fonction publique qui charge modèle + index.
  Appelée en tâche de fond au démarrage de l'application
  (`assistant/api/main.py`, `_cycle_de_vie`), dans un thread séparé
  (`asyncio.to_thread`) pour ne jamais bloquer la boucle d'événements —
  en particulier `/sante`, qui doit rester rapide pour ne jamais risquer
  de dépasser le délai du health-check Clever Cloud (CLAUDE.md, piège
  connu, déjà vécu une fois pour une raison voisine).

Vérifié en local : `/sante` répond en ~30ms immédiatement après le
démarrage, préchauffe en tâche de fond confirmée sans le bloquer. Le
chemin `local_files_only=True` échoue correctement vite (cache vide
dans ce bac à sable, qui n'a de toute façon pas accès à Hugging Face) :
0,3s au lieu de rester bloqué, avant repli sur l'ancien comportement —
pas de régression, échec sandbox nettement plus rapide qu'avant (345ms
contre 700-1800ms habituellement). **Le vrai gain (cache effectif) ne
peut être vérifié qu'en production**, où le modèle est déjà en cache
depuis les déploiements précédents — à confirmer par l'utilisateur lors
du prochain test réel après déploiement.
`verifier_api.py` (7/8, même échec sandbox connu mais plus rapide) et
`verifier_backoffice.py` (12/12) sans régression.

## ✅ Fait le 13/10/2026 — bug de désambiguïsation trouvé via un test réel, corrigé

Test téléphonique réel après la reconciliation du prompt (même trajet
que la veille, Émile Ripert à Velaux → clinique de Marignane) :
l'arrêt de départ, trouvable, n'a pas été trouvé.

**Cause identifiée** (analyse des deux webhooks post-appel) : l'agent a
appelé `rechercher_arret(texte="Émile Ripert", commune="Vitrolles")` —
une commune que l'appelante n'a jamais prononcée (elle a dit "Velaux"),
en violation directe de notre propre règle de prompt. Le paramètre
`commune` filtrant strictement les résultats, le vrai arrêt ("Emil
Ripèr", commune Velaux, confirmé trouvé sans filtre dans un second
appel juste après) est resté hors de portée.

**Hypothèse retenue sur l'origine du mot "Vitrolles"** : l'exemple de
phrase pour la confiance moyenne, dans "Identifier un arrêt", citait
mot pour mot « ... à Vitrolles, ou celui de Marignane ? » — exactement
les deux communes du test réel de l'utilisateur. Fuite probable de
l'exemple du prompt vers le raisonnement du modèle plutôt qu'un vrai
ancrage sur la conversation. Corrigé : les noms de communes réels de
l'exemple remplacés par des espaces réservés génériques
(`[commune A]`/`[commune B]`), pour supprimer la tentation.

**Observation complémentaire, pas corrigée** : pour la destination
("clinique de Marignane"), le premier appel a abandonné après un
`rechercher_repere` vide sans essayer le repli `rechercher_arret`
pourtant explicitement prévu par le prompt ("n'abandonne pas tout de
suite") — alors qu'un second appel, dans la même configuration, a bien
suivi cette règle. Variance du modèle sur une règle déjà écrite, pas
un bug de code identifiable ; à surveiller plutôt qu'à corriger pour
l'instant.

**Non expliqué, hors de portée du code** : l'utilisateur affirme
n'avoir jamais dit "La Réunion" (apparu dans la transcription comme
première tentative de nom d'arrêt) ni "Vélo" (elle dit avoir prononcé
"Velaux" à deux reprises, justement pour éviter la confusion). Pas
d'accès à l'audio depuis cette session pour vérifier — hallucination
possible de la reconnaissance vocale (Scribe v2 Realtime), notée sans
pouvoir trancher.

**Important, pas encore fait** : ce correctif doit être collé dans le
champ "Invite système" côté ElevenLabs pour prendre effet — seule la
phrase d'exemple a changé, l'utilisateur peut éditer directement cette
ligne dans le dashboard plutôt que de tout recoller.

## ✅ Fait le 13/10/2026 — URL du site public réglable depuis le back-office

Point n°1 d'une réflexion plus large de l'utilisateur sur l'alimentation
du corpus documentaire (site web scrapé aujourd'hui, PDF annexes
envisagés pour plus tard, question des conflits entre sources — voir
l'entrée ci-dessous pour le reste, mis de côté).

Investigation d'abord (agent Explore dédié) pour comprendre l'existant
avant de coder — plusieurs découvertes utiles au passage :
- `data/connaissances.md` ("base de connaissance écrite à la main",
  mentionnée dans CLAUDE.md) **n'existe pas et n'a jamais existé** dans
  le dépôt. En réalité, le corpus vient entièrement du site public,
  scrapé automatiquement (`assistant/ingestion/extraire_corpus.py` +
  `extraire_tarifs.py`) vers `data/corpus/*.md` (non versionné, recalculé
  à la demande), puis chunké et vectorisé par `indexer_corpus.py` vers
  `data/corpus_index.json` (lui, versionné — seul fichier de `data/`
  excepté de `.gitignore`). CLAUDE.md est resté sur une intention jamais
  concrétisée — à corriger à l'occasion, pas fait dans cette session.
- `data/config.yaml` a déjà un champ `site_web`, avec un commentaire
  disant qu'il sert de source au scraper — mais **rien ne le lisait
  réellement** : l'URL était écrite en dur dans `extraire_corpus.py`
  (`BASE_URL`) et `extraire_tarifs.py` (`URL_BASE`). Incohérence
  préexistante, pas une fonctionnalité construite depuis zéro.

**Implémenté** : `site_web()` (nouvelle fonction dans
`assistant/ingestion/extraire_corpus.py`) lit un réglage back-office
(table `parametres`, même mécanisme que `format_sms`) avec la valeur de
`config.yaml` comme repli si rien n'a encore été réglé — un réseau
dupliqué peut donc changer son site sans toucher au code ni redéployer,
contrairement à `config.yaml` qui est versionné dans Git. 
`extraire_tarifs.py` réutilise cette même fonction (son `URL_BASE`
combinait déjà domaine + chemin spécifique à la page tarifs, désormais
séparés : `site_web()` + `CHEMIN_TARIFS`). Nouvelle carte "Site public
du réseau" dans l'onglet Paramétrage (`assistant/backoffice/page.py`),
route `POST /backoffice/parametres/site_web` (`assistant/api/main.py`)
qui rejette une valeur ne commençant pas par `http://`/`https://` sans
toucher au réglage existant.

**Important, à retenir** : ce réglage ne prend effet qu'au **prochain**
`assistant.corpus --refresh` — il ne change rien rétroactivement au
corpus déjà indexé et versionné. Mentionné dans la carte back-office
elle-même pour que ça ne surprenne personne.

Vérifié en local : repli vers `config.yaml` confirmé quand rien n'est
réglé, réglage effectif après `definir_parametre`, retour au repli après
suppression du réglage. Route testée : valeur valide acceptée et
persistée, valeur invalide (sans `http`) rejetée avec message d'erreur
affiché, ancienne valeur conservée. `verifier_api.py` (7/8, échec réseau
sandbox connu) et `verifier_backoffice.py` (12/12) sans régression.

## 🔶 Mis de côté le 13/10/2026 — documents annexes (PDF) et conflits entre sources

Suite de la réflexion ci-dessus, explicitement non développée à la
demande de l'utilisateur : elle voulait d'abord "y voir plus clair"
avant tout code. Deux questions posées, deux réponses de principe,
rien d'implémenté :

**Ajouter des PDF (ex. formulaire papier d'abonnement scanné) au
corpus** : techniquement faisable en réutilisant le même pipeline
(texte → chunks → embeddings → même recherche), mais deux vraies
complications structurelles :
- **Stockage** : le contenu scrapé du site n'a jamais besoin d'être
  conservé (re-scrapable à volonté) ; un PDF uploadé par l'équipe n'a
  pas de "source" à re-télécharger — il faudrait vivre dans `data/etat/`
  (seul dossier qui survit aux déploiements Clever Cloud), pas dans
  `data/` comme le reste du corpus aujourd'hui.
- **Déclenchement de l'ingestion** : aujourd'hui, mettre à jour l'index
  est une suite manuelle (CLI, vérification, commit Git) précisément
  pour éviter de recalculer les embeddings à chaque déploiement (voir
  CLAUDE.md, piège connu). Un vrai espace de dépôt autonome demanderait
  un bouton "réindexer" en back-office qui calcule en tâche de fond et
  écrit dans `data/etat/` — ce qui découple `corpus_index.json` de sa
  nature actuelle de fichier versionné dans Git, un changement de fond.

**Conflits entre sources (ex. 1,20 € sur le site vs 1 € sur un PDF)** :
le système actuel n'a aucune notion de conflit — `rechercher_information`
renvoie le chunk le mieux classé sans savoir qu'un autre chunk dit autre
chose. Résolution automatique écartée (risque réel d'usine à gaz, et
pas fiable avec notre seul pipeline à base d'embeddings). Direction
retenue, reprenant l'intuition de l'utilisateur (comparatif rouge/vert
vu lors de la publication du prompt ElevenLabs) : à chaque ajout de
document, repérer les paires de chunks de la même catégorie
sémantiquement très proches mais contenant des valeurs numériques
différentes, et les signaler côte à côte à l'admin pour arbitrage manuel
avant mise en ligne — jamais d'arbitrage automatique par le système
lui-même.

**Pas de suite prévue avant la validation de l'expérimentation en
cours**, comme l'utilisateur l'a proposé elle-même.

## ✅ Fait le 13/10/2026 — fichier de référence du prompt réconcilié avec le réel

En publiant les changements de latence (voir entrée ci-dessous),
l'utilisateur a repéré via le comparatif ElevenLabs que le prompt
réellement en ligne contenait des instructions absentes de notre
fichier `docs/spec-assistant-vocal-v0-revisee.md` — du contenu ajouté
directement dans le dashboard à un moment, jamais reporté dans le
dépôt. CLAUDE.md dit que ce fichier "fait autorité" ; ce n'était plus
vrai dans les faits. Bon réflexe de l'utilisateur de vérifier le
comparatif avant de publier plutôt qu'après.

**Récupéré depuis le live (absent du fichier, maintenant réintégré)** :
- la formulation exacte de la question de satisfaction en fin d'appel
- les balises audio `[avec empathie]` / `[avec patience]`
- la gestion d'un outil en panne (explique l'indisponibilité, propose
  transfert ou rappel) — **deux versions quasi dupliquées de cette
  règle coexistaient en live** (une version rigide "systématiquement",
  une version "si la situation s'y prête") ; la seconde a été gardée,
  la première supprimée, avec l'accord de l'utilisateur
- la réponse sur le site internet du réseau
- la formule de clôture chaleureuse avec `{{formule_cloture}}`
- absence de section "## Ouverture" dans le prompt système : le
  message d'accueil est géré par le champ séparé "Premier message"
  côté ElevenLabs, pas dupliqué dans le prompt — le fichier de
  référence la contenait encore à tort, retirée

**Autre anomalie trouvée et corrigée en même temps** : un paragraphe
sur les conditions d'éligibilité de `rechercher_information` s'était
retrouvé collé en plein milieu de la section "Objets perdus" côté
live (hors sujet à cet endroit) — jamais présent dans notre fichier,
qui l'avait toujours au bon endroit ("Répondre sur le commercial et le
pratique"). Un deuxième point d'interrogation en trop dans "Sorties"
("un numéro ? ?") a aussi été corrigé au passage, côté live uniquement.

**Ajouté au passage** : la partie "préférence de trajet" (moins de
marche / moins de correspondances, priorité n°3, codée il y a 2 jours)
n'avait jamais été collée dans le prompt live — le code existait mais
l'agent ne savait pas que la fonctionnalité existait. Ajoutée en même
temps que la réconciliation.

Le fichier `docs/spec-assistant-vocal-v0-revisee.md` §5 correspond
maintenant exactement au prompt publié côté ElevenLabs (vérifié ligne
à ligne). **Pour la suite** : signaler explicitement à chaque fois
qu'un changement de prompt doit être collé côté ElevenLabs — ça ne
prend jamais effet automatiquement, un oubli de collage était
justement à l'origine de l'écart "préférence" ci-dessus.

## ✅ Fait le 13/10/2026 — latence perçue (priorité n°5)

Investigation menée avant tout code : recherche sur les mécanismes
natifs ElevenLabs pour la latence perçue (indépendants de notre propre
prompt). Deux trouvés dans la documentation publique ElevenLabs :
- **Tool Call Sounds** (son joué pendant qu'un outil tourne — clavier,
  musique d'ascenseur) : écarté par l'utilisateur, moins naturel qu'un
  mot phatique selon elle.
- **Soft timeout / messages de remplissage** (`soft_timeout_config`,
  jusqu'à 7 formules + randomisation) : documenté côté API et dans le
  guide "Conversation flow", mais **introuvable dans le dashboard de
  l'utilisateur** après exploration complète (onglet Agent, Paramètres
  > Avancé en entier, Workflow) — fonctionnalité probablement pas
  encore déployée côté interface, ou réservée à un palier différent ;
  pas de certitude sur la cause exacte, pas vérifiable depuis
  l'extérieur du compte. **Mis de côté**, pas supprimé : les 7 formules
  préparées restent utilisables si la fonctionnalité apparaît un jour.
  7 formules préparées pour mémoire : « Un instant, je vérifie ça pour
  vous. », « D'accord, je regarde ça tout de suite. », « Je consulte
  nos informations, merci de patienter. », « Très bien, laissez-moi
  vérifier. », « Je continue la recherche de mon côté. », « Voyons voir
  ce que je peux vous dire. », « Ne quittez pas, je m'occupe de ça. »

**Erreur corrigée en session** : une première version du changement de
prompt supprimait la phrase de transition systématique avant les
outils rapides, en s'appuyant sur le soft timeout ElevenLabs comme
filet de sécurité de repli — avant de découvrir qu'il n'est pas
accessible. Cette version aurait fait régresser la latence perçue
(plus aucun filet du tout sur les outils rapides qui seraient
exceptionnellement lents). Corrigée avant que l'utilisateur ne colle
le prompt dans ElevenLabs.

**Côté prompt, fait (version corrigée)** : la règle "Style oral"
garde la phrase de transition systématique avant chaque appel d'outil
(comportement inchangé). Deux exceptions nommées s'y ajoutent, où la
phrase explique en plus POURQUOI l'attente est plus longue que
d'habitude, style "contrôleur de train", plutôt que de dire juste "un
instant" : avant calculer_itineraire_complexe (service Google externe)
et quand une recherche d'arrêt enchaîne plusieurs outils pour résoudre
un itinéraire. Fichier modifié : `docs/spec-assistant-vocal-v0-revisee.md`,
§5. Le prompt complet mis à jour a été donné à l'utilisateur en
conversation pour collage manuel dans le champ "Invite système" côté
ElevenLabs (jamais automatique — à refaire à chaque modification de
cette section).

**Publié par l'utilisateur** (voir aussi l'entrée "fichier de référence
du prompt réconcilié" juste au-dessus, trouvée en cours de publication).
Soft timeout à revisiter si la fonctionnalité apparaît un jour dans le
dashboard — les 7 formules restent prêtes.

## ✅ Fait le 13/10/2026 — 4 améliorations du back-office (priorité n°4 + opportunité)

Priorité n°4 (satisfaction démesurée dans le graphe des motifs) traitée
en même temps que 3 autres améliorations du back-office identifiées
par l'utilisateur au même moment, toutes dans la même zone de l'écran
Suivi.

**1. Satisfaction sortie du graphe des motifs d'appels** —
`enregistrer_satisfaction` est maintenant filtré de `repartition_outils`
(`assistant/backoffice/appels.py`), même logique que `rechercher_arret`
déjà exclu (posé en fin de presque tout appel, ce n'est pas un motif
d'appel en soi). En contrepartie, la tuile "Satisfaction client" affiche
maintenant une deuxième ligne : le taux de réponse à la sollicitation
elle-même (SMS d'appels captés ayant une réponse enregistrée), pour
donner une idée de la fiabilité du taux de satisfaction affiché
au-dessus — une poignée de réponses sur beaucoup d'appels pèse moins
qu'un fort taux de réponse.

**2. Histogramme horaire affiné à la tranche de 15 minutes** —
`repartition_appels_par_heure()` renommée `repartition_appels_par_quart_heure()`
(96 compteurs au lieu de 24, `assistant/backoffice/appels.py`), SVG
redessiné pour 96 barres plus fines (`_svg_repartition_horaire`,
`assistant/backoffice/page.py`) avec le nombre ET le pourcentage par
rapport au total dans l'info-bulle de chaque barre (ex. "9h00 : 3
appels (12%)").

**3. Tableau des appels limité à 10 lignes + chevron pour tout dérouler**
— au-delà des 10 appels les plus récents (déjà triés du plus récent au
plus ancien), les lignes sont repliées directement dans le HTML
(`style="display:none"` posé côté serveur, jamais par un JS tardif qui
ferait clignoter la liste complète à l'ouverture). Un bouton
"▼ Voir les N appels précédents" en bas à droite du tableau les
affiche tous (bascule, peut se replier à nouveau). Le filtre par jour
continue de fonctionner sur l'ensemble des appels, pas seulement les
10 visibles : sélectionner un jour montre toutes les lignes de ce jour
même repliées par défaut.

**4. Bouton "copier" sur la charge brute du webhook** — un petit bouton
📋 apparaît une fois le détail ouvert (à l'intérieur du `<details>`,
donc après avoir cliqué sur le chevron), copie tout le texte via
`navigator.clipboard.writeText`, confirmation visuelle "✅ Copié"
pendant 1,5s. Répond à un problème concret rencontré en session :
sélectionner à la main une charge JSON complète pour me la copier-coller
était long et source d'erreur.

Vérifié en local : comptage par tranche de 15 min testé explicitement
(3 appels à 9h12-9h14 → tranche "9h00", 2 à 9h47-9h48 → tranche "9h45",
1 à 18h03 → tranche "18h00", tous comptés dans le bon panier). Rendu de
la tuile satisfaction, du graphe 96 barres, et du chevron (12 appels de
test insérés, "26 appels précédents" affiché et cohérent avec le total
réel en base, vérifié avant nettoyage) confirmés directement dans le
HTML rendu. `verifier_api.py` (7/8, échec réseau sandbox connu) et
`verifier_backoffice.py` (12/12) relancées sans régression.

**Reste à faire** : rien d'identifié côté code. Le point "paramétrage
alimenté par des documents annexes" évoqué par l'utilisateur est
explicitement reporté à une session suivante, pas commencé.

## ✅ Fait le 13/10/2026 — choix entre trajets ("moins de marche" / "moins de correspondances")

3e des 5 priorités du 12/10. Investigation menée en deux volets avant
tout code, à la demande de l'utilisateur : ce que Google Routes permet
techniquement, et comment ça se traduit en parcours voix. Décision
prise ensemble : la latence reste juge de paix (voir CLAUDE.md), donc
**rien n'est demandé par défaut** — le trajet Google par défaut reste
la seule réponse annoncée d'emblée, un second appel (plus lent, donc
assumé) n'est déclenché que si l'appelant exprime lui-même une
contrainte.

**Ce que l'API permet** (vérifié dans la référence Routes API v2, pas
dans l'app Google Maps grand public qui a des fonctionnalités que
l'API n'expose pas) :
- `transitPreferences.routingPreference` = `LESS_WALKING` ou
  `FEWER_TRANSFERS` : un seul trajet biaisé selon le critère choisi,
  pas une liste à comparer. Un second appel Google à chaque usage.
- `computeAlternativeRoutes` (jusqu'à 3 alternatives, classement
  opaque de Google, pas un critère qu'on choisit) : écarté — pas
  exploitable pour une réponse orale claire, et pas de contrôle sur ce
  qui différencie les trajets proposés.
- Aucun paramètre d'accessibilité fauteuil roulant dans l'API Routes
  (c'est une fonctionnalité de l'app Google Maps grand public depuis
  2018, jamais exposée aux développeurs).

**Investigation complémentaire, notre propre GTFS** : les colonnes
`wheelchair_boarding` (stops.txt) et `wheelchair_accessible` (trips.txt)
existent bien dans le flux de ce réseau, mais sont renseignées à
**100% avec la valeur "0"** (= "aucune information", au sens strict de
la norme GTFS) sur les 1307 arrêts et 3591 trajets vérifiés. Même
constat que pour l'API Google : l'accessibilité fauteuil roulant n'est
**pas exploitable aujourd'hui**, ni par Google Routes ni par notre
propre GTFS. Sujet mis de côté (non prioritaire), mais au moins
tranché : il faudrait une tout autre source de données pour avancer un
jour, pas un réglage à activer sur l'existant.

**Point soulevé par l'utilisateur, à garder en tête sans agir
maintenant** : les aléas climatiques (pluie, mais aussi fortes
chaleurs) dégradent l'expérience de mobilité multimodale (marche,
attente, report modal vers le bus) — "moins de marche" répond déjà au
besoin immédiat sans donnée météo, mais la question de la chaleur
comme variable d'ajustement de mobilité est identifiée comme un sujet
d'avenir, pas pour ce POC.

**Implémenté** :
- `calculer_itineraire_complexe(..., preference=None)` (`assistant/
  outils/itineraire_google.py`) : `preference` vaut `"moins_marche"` ou
  `"moins_correspondances"`, mappé vers `LESS_WALKING`/`FEWER_TRANSFERS`
  côté Google. Absent par défaut : le corps de la requête Google est
  identique à avant (`transitPreferences` n'apparaît que si demandé) —
  latence du cas courant inchangée. Préférence inconnue → erreur
  propre (`trouve: false`), jamais d'exception.
- `preference` ajouté aux schémas `ItineraireComplexeRequete` et
  `EnvoiSmsItineraireRequete` (`assistant/api/schemas.py`), propagé
  dans les deux routes (`assistant/api/main.py`) et dans
  `envoyer_sms_itineraire` (`assistant/outils/sms.py`) — le SMS doit
  recalculer le même trajet que celui annoncé à l'oral, jamais le
  trajet par défaut si une préférence a été exprimée.
- Contrats mis à jour dans `docs/spec-assistant-vocal-v0-revisee.md`
  (§4) et nouvelle règle de prompt (§5, section Itinéraire) : l'agent
  ne propose JAMAIS ce choix de sa propre initiative, seulement en
  réaction à une contrainte exprimée par l'appelant, avec une phrase de
  transition avant le second appel, et le nouveau trajet annoncé comme
  un remplacement, jamais une liste à comparer.

Vérifié en local : préférence invalide rejetée proprement (par l'outil
lui-même et par Pydantic, 422, sans toucher le réseau ni le GTFS) ;
corps de la requête Google inspecté directement (en interceptant
l'appel HTTP) — `transitPreferences` présent seulement si une
préférence est passée, absent sinon (comportement par défaut
inchangé, confirmé). `verifier_api.py` (7/8, échec réseau sandbox
connu) et `verifier_backoffice.py` (12/12) relancées sans régression.

**Reste à faire** : rien d'identifié côté code — à l'usage réel, il
faudra vérifier que l'agent respecte bien la règle "jamais par
défaut" en conditions réelles d'appel (comme pour toute règle de
prompt).

## ✅ Fait le 13/10/2026 — décompte des SMS envoyés au back-office

Finalise le chantier SMS (voir entrée juste au-dessous) avant de passer
à la priorité n°3. Tâche qui avait été mise de côté le temps de
stabiliser le format : repurposer la tuile "Horaire moyen des appels"
(devenue redondante avec l'histogramme horaire du 13/10 au matin) en
compteur de SMS envoyés.

Choix fait entre les deux options évoquées le 12/10 (API Twilio vs
estimation par un facteur de coût) : **ni l'un ni l'autre tel
qu'envisagé** — calcul exact fait nous-mêmes à partir du texte déjà
conservé dans `sms_envoyes.texte`, sans appel réseau supplémentaire ni
estimation approximative. Le nombre de segments facturés dépend de
l'encodage (GSM-7 ou UCS-2) et de la longueur exacte du texte envoyé,
qu'on a déjà — pas besoin d'interroger Twilio pour ça, et plus fiable
qu'un facteur multiplicateur générique (CLAUDE.md, exactitude).

**Implémenté** :
- `_compte_segments(texte)` (`assistant/outils/sms.py`) : applique les
  règles GSM-7 (160 car. en 1 segment, 153/segment ensuite) ou UCS-2
  (70 puis 67) selon que le texte est entièrement ASCII ou pas — nos
  deux formats ne mélangent jamais les deux, donc cette distinction
  simple suffit (pas besoin de la table complète de l'alphabet GSM-7
  étendu).
- `resumer_sms()` : agrège les SMS **réussis uniquement** (un échec
  n'est jamais facturé) — nombre de SMS et nombre réel de segments.
- Tuile "Horaire moyen des appels" remplacée par "SMS d'itinéraire
  envoyés" (nombre + segments facturés en sous-libellé) dans
  `assistant/backoffice/page.py`. Le calcul `horaire_moyen` lui-même a
  été retiré de `resumer_tracabilite()` (`assistant/backoffice/appels.py`)
  — devenu mort depuis qu'il n'est plus affiché nulle part.

Vérifié en local : segments comptés testés sur plusieurs longueurs
(160/161/306/307 caractères ASCII, 70/71 caractères emoji) — tous
corrects. `resumer_sms()` testé avec 2 SMS réussis (3 + 1 segments) et
1 échec inséré en base, confirmé que l'échec n'est pas compté. Rendu de
la tuile vérifié dans la page (état "à venir" tant qu'aucun SMS réel
n'a été envoyé). `verifier_api.py` (7/8, échec réseau sandbox connu) et
`verifier_backoffice.py` (12/12) relancées sans régression.

## ✅ Fait le 13/10/2026 — format du SMS d'itinéraire configurable (emoji / texte)

2e des 5 priorités notées le 12/10. Point de départ : l'utilisateur a
partagé une maquette de SMS travaillée en parallèle sur un autre projet
("B2 Pictogrammes complets" — en-tête récapitulatif, temps d'attente
par correspondance, chiffres encerclés, arrivée finale mise en valeur).
4 consignes explicites : garder la version emoji pour les démos mais
remplacer les chiffres encerclés par du texte simple ; prévoir (plus
tard, tâche mise de côté) un comptage de SMS envoyés au back-office ;
**garder aussi** une version 100% texte (sans emoji) ; rendre le choix
entre les deux réglable depuis "Paramétrage".

Raison de garder les deux formats : n'importe quel emoji force tout le
SMS en encodage UCS-2 (70 car./segment au lieu de 160 en GSM-7) — notre
version emoji déjà en prod coûtait 8 segments pour un trajet à 3
étapes, une version texte équivalente n'en coûte que 3.

**Implémenté** :
- Table `parametres` (clé/valeur, `assistant/outils/db.py`) pour les
  petits réglages du back-office — clé/valeur plutôt qu'une colonne
  dédiée, un 2e cas d'usage (source du comptage SMS) est déjà identifié.
  `obtenir_parametre`/`definir_parametre` par-dessus.
- `assistant/outils/sms.py` réécrit : un calcul partagé
  (`_preparer_contexte_sms`) déduit le temps d'attente avant chaque bus
  et l'heure d'arrivée finale réelle à partir des horaires déjà connus
  (jamais inventé — None et simplement pas affiché si une donnée
  manque), puis deux formateurs (`_formater_sms_emoji`,
  `_formater_sms_texte`, numérotation "1.", "2." en texte simple)
  construisent le texte à partir du même résultat. `formater_sms_itineraire`
  choisit le format via le paramètre `format_sms` (défaut "emoji").
- `calculer_itineraire_complexe` renvoie maintenant `destination` (le
  nom d'arrêt vérifié de notre propre GTFS), pour que le SMS annonce
  "Arrivée à X" sans dépendre d'une reformulation de Google.
- Carte "Format du SMS d'itinéraire" dans l'onglet Paramétrage
  (`_carte_format_sms`, `assistant/backoffice/page.py`) + route
  `POST /backoffice/parametres/format_sms`.

Vérifié en local : calcul des temps d'attente et de l'heure d'arrivée
testé sur un trajet à 2 correspondances (résultats corrects) ; version
texte vérifiée 100% ASCII par un test explicite. Bascule emoji/texte
testée via la carte du back-office (persistance confirmée en relisant
le paramètre). `verifier_api.py` (7/8, échec réseau sandbox connu) et
`verifier_backoffice.py` (12/12) relancées sans régression.

**Reste à faire** : le comptage des SMS envoyés dans le back-office
(tuile "Horaire moyen" à repurposer), explicitement mis de côté par
l'utilisateur jusqu'à la fin de ce chantier-ci.

## ✅ Fait le 13/10/2026 — graphique "Appels par heure de la journée"

Première des 5 priorités notées hier soir. Choix fait avec l'utilisateur :
version native dans notre propre back-office plutôt que "Claude
Dashboards" (fonctionnalité Anthropic trouvée très récente, pas assez
de certitude pour la recommander aujourd'hui) — mis de côté, pas
exclu pour plus tard, les deux ne s'excluent pas.

**Implémenté** :
- `repartition_appels_par_heure()` (`assistant/backoffice/appels.py`) :
  24 compteurs (0h-23h), même filtre que `resumer_tracabilite`
  (`duree_secs IS NOT NULL`, pour ignorer les lignes incomplètes/test).
- Histogramme en barres dessiné à la main en SVG
  (`_svg_repartition_horaire`, `assistant/backoffice/page.py`) — même
  logique "pas de librairie de graphiques" que le donut des motifs
  d'appels déjà existant. Info-bulle par barre (heure + nombre
  d'appels). Placé en carte pleine largeur sous les tuiles
  d'indicateurs (pas à côté du donut, qui est pensé pour une colonne
  étroite — un histogramme de 24 barres a besoin de plus de place).

Vérifié en local : agrégation testée explicitement (3 appels factices à
9h, 2 à 18h → `[0,...,3,...,2,...]` correct), rendu confirmé via les
info-bulles de la page. Suites `verifier_api.py` (7/8, démarrage à
froid confirmé sans rapport) et `verifier_backoffice.py` (12/12)
relancées sans régression.

**Reste à faire** : rien d'identifié pour l'instant — à l'usage,
l'utilisateur pourra demander une granularité plus fine (tranches de
15 min, évoqué hier comme "peut-être") si l'histogramme horaire ne
suffit pas.

## ✅ Résolu le 12/10/2026 — appels téléphoniques réels absents du back-office

Signalé une 2e fois par l'utilisateur : un vrai appel téléphonique
(numéro Twilio) n'apparaît pas du tout dans `/backoffice/appels`, même
après rafraîchissement et en navigation privée (élimine un problème de
cache navigateur). Investigation menée ensemble, étape par étape :

1. **Écarté** : notre serveur accepte toujours le webhook correctement
   (`curl` direct sur `/webhooks/elevenlabs/fin_appel` → 200). Rien
   cassé côté authentification/réseau par les changements du jour.
2. **Écarté** : republication du webhook post-appel côté ElevenLabs
   (resélectionné + republié par précaution) — n'a pas résolu le
   problème, donc pas (seulement) un souci de publication oubliée.
3. **Signal clé trouvé** : un test via le **widget** ElevenLabs (pas un
   appel téléphonique) apparaît, lui, correctement dans le back-office,
   presque immédiatement. **Tous les appels manquants à ce jour étaient
   des vrais appels téléphoniques Twilio ; la seule vérification
   réussie depuis la rotation du jeton (09/10) était aussi un test
   widget.** Forte présomption que le problème est spécifique au canal
   téléphonique, pas aux webhooks en général — à confirmer avec
   d'autres tests, et à chercher du côté d'un éventuel réglage propre
   au numéro Twilio/à l'intégration téléphonique côté ElevenLabs,
   séparé des réglages génériques de l'agent déjà vérifiés.

**Deux vrais bugs de robustesse trouvés et corrigés en creusant**
(indépendants de la cause ci-dessus, mais qui auraient de toute façon
pu faire perdre silencieusement un appel ou planter toute la page) :

- `enregistrer_appel()` (`assistant/backoffice/appels.py`) : le
  commentaire du code promettait "ne lève jamais d'exception sur un
  format inattendu", mais `_extraire_tracabilite()` n'était pas
  réellement blindée contre toute forme de payload — jamais vérifiée
  sur un vrai appel téléphonique. Un seul champ de forme inattendue
  (ex. `transcript` non conforme) faisait perdre **tout l'appel**
  plutôt qu'une seule métrique. Corrigé : `try/except` autour de
  l'extraction, repli sur des métriques vides si elle échoue — la
  ligne (conversation_id, payload brut complet) est maintenant
  toujours insérée.
- `_transcription_appel()` (`assistant/backoffice/page.py`) : même
  angle mort côté affichage — un `transcript` de forme inattendue
  faisait planter **toute la page** `/backoffice/appels` (pas
  seulement la ligne concernée), trouvé en testant le correctif
  ci-dessus avec un payload volontairement cassé. Corrigé : les tours
  de transcript qui ne sont pas des objets valides sont ignorés plutôt
  que de faire planter le rendu.

Vérifié en local : payload cassé (transcript avec un élément non-objet)
→ avant le correctif, perte totale de l'appel ET plantage de la page ;
après, ligne conservée (métriques vides) et page affichée normalement
(200). Nettoyage des lignes de test fait avant de relancer les suites.
`verifier_api.py` (7/8, échec réseau sandbox connu) et
`verifier_backoffice.py` (12/12) relancées sans régression.

**Reste ouvert** :
- La cause réelle du silence côté téléphonie Twilio n'est pas encore
  trouvée — à investiguer côté ElevenLabs (réglage propre au numéro,
  pas à l'agent générique).
- Deux bugs signalés par l'utilisateur en testant via le widget, pas
  encore traités (méthode "une chose à la fois") :
  - La question de satisfaction est validée par l'agent sans que
    l'appelant y réponde — **récidive** d'un bug déjà corrigé le
    28/09/2026 par une règle de prompt (jamais appeler
    `enregistrer_satisfaction` dans le même tour que la question). La
    règle existe toujours dans la spec — à vérifier si elle est
    toujours bien copiée côté ElevenLabs, ou si le problème est plus
    profond qu'une consigne de prompt.
  - Colonne "Voix" vide pour plusieurs appels dans le tableau du
    back-office, signalé comme un problème récurrent, antérieur à
    aujourd'hui — **confirmé comme non séparé** en relisant le tableau
    avec l'utilisateur : toutes les lignes à voix manquante
    correspondaient à des appels "à venir" (incomplets) ou à 0 seconde
    — même cause que l'absence d'appels, pas un second bug.

**Cause racine trouvée et corrigée** : le webhook post-appel
("Service CRC...") avait été recréé lors de l'incident `API_TOKEN` du
09/10, et marchait une seule fois (un test widget) avant de rester
silencieux pour tous les vrais appels téléphoniques depuis. Hypothèse
confirmée via la documentation ElevenLabs (webhook désactivé
automatiquement après trop d'échecs consécutifs) croisée avec le bug
de robustesse trouvé le même soir (`_extraire_tracabilite` qui
plantait sur un format de payload imprévu → notre serveur renvoyait
une erreur à chaque vrai appel → échecs comptabilisés côté ElevenLabs).
Resélectionner le webhook existant n'a pas suffi ; **le recréer
entièrement** (même procédure que pour la rotation de jeton) a résolu
le problème. Confirmé par un vrai appel réel reçu en back-office avec
toutes ses métadonnées.

**⚠️ Nouvel incident d'exposition d'`API_TOKEN`, 4e cette semaine** :
l'utilisateur a partagé le payload complet du webhook de cet appel
réussi pour permettre l'analyse — payload très utile, mais contenait le
jeton en clair dans chaque `tool_calls` (en-tête `Authorization`).
Rotation relancée aux 4 endroits habituels, cette fois 11 outils (les 9
historiques + les 2 ajoutés cette semaine). Proposé à l'utilisateur :
réflexe de rédaction (remplacer les valeurs d'`Authorization` par
"REDACTED" avant de coller un payload), ou un petit script de
nettoyage local si elle préfère — à mettre en place si l'utilisateur le
souhaite, pas encore fait.

## 📋 Priorités pour la prochaine session (notées le 12/10/2026 soir, par l'utilisateur)

Dans l'ordre donné par l'utilisateur :

1. **Suivi des appels par courbe** (pics horaires, heures pleines/creuses,
   éventuellement par tranche de 15 min) — déjà noté plus haut dans ce
   fichier (entrée "Idées back-office" du 12/10) comme non prioritaire ;
   devient la priorité n°1 pour la prochaine session. Question ouverte
   posée par l'utilisateur : **"Claude Dashboards"** (fonctionnalité
   Anthropic très récente, lancée en bêta le 08/10/2026 d'après une
   seule source trouvée, pas confirmée directement) pourrait-il servir
   à construire cet écran ? Pas de réponse tranchée donnée ce soir,
   faute de connaissance directe de l'outil — à explorer ensemble, sans
   exclure la voie plus simple (graphique construit directement dans
   notre propre back-office, données déjà disponibles).
2. **Améliorer encore la lisibilité du SMS** — l'utilisateur dit y
   réfléchir de son côté, pas d'idée précise encore partagée.
3. **Explorer le choix entre plusieurs itinéraires proposés par Google**
   (pas seulement le premier résultat) — cas d'usage donné par
   l'utilisateur : un trajet direct nécessitant 25 min de marche vs un
   trajet avec correspondance n'en nécessitant que 10, pertinent par
   exemple en cas de pluie (lien avec l'idée météo déjà notée le
   08/10) ou pour une personne ayant des difficultés à marcher.
   L'utilisateur évoque aussi, comme extension possible mais non
   prioritaire, une préférence pour des lignes accessibles aux personnes
   à mobilité réduite — à condition de savoir un jour récupérer cette
   information (pas vérifié si le GTFS ou Google Routes l'expose).
4. **Revoir le graphe de répartition des cas d'usage du back-office** :
   la part "satisfaction" y apparaît démesurée, alors que c'est normal
   puisque la question est posée à chaque appel — biais de lecture du
   graphique actuel à corriger, pas un bug.
5. **Latence perçue, toujours en chantier** — la restructuration du
   prompt faite aujourd'hui (avant/pendant calculer_itineraire_complexe)
   a aidé mais ne suffit pas complètement selon l'utilisateur
   ("Pour l'instant retenus à quai" reste l'objectif) ; à retravailler
   ensemble, au-delà de la seule règle de prompt déjà posée.

## ✅ Fait le 12/10/2026 — bug de marches dupliquées corrigé, SMS simplifié, 5 nouveaux retours UX

Deuxième appel réel avec les outils déclarés : ça fonctionne, mais les
captures du SMS reçu (partagées par l'utilisateur) ont révélé un vrai
bug trouvé en analysant les images, pas seulement un ressenti UX :
**Google découpe parfois une seule marche réelle en plusieurs steps
techniques** (ex. traverser une rue devient un step à part), donc le
SMS affichait "Marche" 3 fois pour un même trajet à pied, et une
"Marcher vers Pierre Plantée" juste après "Descendre à Pierre Plantée"
(artefact de changement de quai/écart de coordonnées).

**Corrigé dans `assistant/outils/itineraire_google.py`** :
- Les steps de marche consécutifs sont fusionnés en une seule étape
  (durées additionnées), au lieu d'une ligne par step technique.
- Une marche "vers" un arrêt où l'on est déjà (même nom que la dernière
  descente, ou le départ initial) est supprimée si elle est courte ou
  de durée inconnue — une vraie marche de plusieurs minutes vers un
  arrêt de même nom reste affichée (testé explicitement pour ne pas
  perdre d'information réelle).

**5 autres retours traités** :
1. SMS simplifié : une seule heure par étape (départ), plus
   depart→arrivée à chaque ligne — la durée totale suffit pour le
   reste.
2. Lien Google Maps raccourci : coordonnées arrondies à 5 décimales
   (~1 m de précision, largement suffisant), le lien reste présent
   mais nettement plus court.
3. L'outil `envoyer_sms_itineraire` demande maintenant prénom **et**
   nom (pas de nouvelle colonne : même convention que `demander_rappel`,
   les deux dans le champ `nom` existant).
4. Stockage/export déjà en place depuis le tour précédent (`nom` dans
   `sms_envoyes.csv`) — confirmé à l'utilisateur, rien à ajouter.
5. **Latence perçue à l'interprétation de la demande** (avant même le
   premier outil, pas seulement calculer_itineraire_complexe) : règle
   "Style oral" renforcée — une phrase de transition courte **avant
   chaque appel d'outil, systématiquement**, pas seulement quand
   l'outil "semble" lent. Limite honnête notée pour l'utilisateur : le
   LLM n'a pas de minuteur, il ne peut pas détecter "2-3 secondes se
   sont écoulées" en direct — la seule traduction fiable en prompt est
   une règle inconditionnelle, pas une réaction au silence réel. À
   vérifier si ElevenLabs propose un mécanisme natif indépendant du
   LLM (ex. message programmé pendant l'exécution d'un outil) —
   question posée à l'utilisateur, pas vérifiable depuis cet
   environnement (interface ElevenLabs bloquée).

**Point non résolu, à investiguer** : l'utilisateur signale pour la
2e fois un appel réel absent du back-office (`/backoffice/appels`),
l'empêchant de partager les logs. Pas encore élucidé — questions
posées (appel réel via le numéro Twilio ou test widget ? la page a-t-elle
été rafraîchie après l'appel ?). Piste de secours proposée : récupérer
le payload du webhook directement depuis l'historique des conversations
côté ElevenLabs si notre back-office ne le montre vraiment pas.

Vérifié en local : fusion des marches testée explicitement sur le cas
exact vu dans les captures (3 marches consécutives → 1 seule), non-
suppression d'une vraie marche de 7 minutes vérifiée séparément. Suites
`verifier_api.py` (7/8, échec réseau sandbox connu) et
`verifier_backoffice.py` (12/12) relancées sans régression.

## ✅ Fait le 12/10/2026 — premier appel réel complet réussi, 5 retours UX de l'utilisateur traités

Premier appel de bout en bout avec les deux outils déclarés côté
ElevenLabs et la consigne de prompt stabilisée : **ça fonctionne**.
Cinq retours de l'utilisateur après ce test, traités un par un :

1. **Latence perçue avant le calculateur complexe** — prompt-only :
   l'agent annonce maintenant qu'il continue à chercher avant d'appeler
   calculer_itineraire_complexe, au lieu de laisser un silence.
2. **Débit trop rapide à l'énoncé du trajet, risque d'interruption** —
   deux leviers pris ensemble : l'agent annonce d'abord la complexité du
   trajet ET mentionne l'existence du SMS *avant* de détailler (pour que
   l'appelant sache qu'il n'a pas besoin de tout noter dès le début,
   pas seulement après). Le troisième levier qu'avait évoqué
   l'utilisateur (ralentir réellement le débit vocal) n'a pas été
   ajouté au prompt — pas de certitude que les balises audio v3
   ([lentement], etc.) soient fiables pour ça sans l'avoir testé en
   vrai ; proposé à l'utilisateur comme piste à essayer elle-même.
3. **Prénom non demandé, utile pour personnaliser le SMS** — nouveau
   paramètre optionnel `nom` sur `envoyer_sms_itineraire` (Pydantic,
   route, table `sms_envoyes` migrée via `_migrer_colonnes_manquantes`
   car déjà en production). Le SMS s'ouvre sur "Bonjour {nom}," si
   fourni, sinon reste générique — jamais bloquant si l'appelant ne le
   donne pas.
4. **Structure du SMS à revoir** (comparée à Google Maps) : ligne +
   direction (panneau du bus) + arrêt de descente maintenant affichés
   séparément, plus "Marcher vers [arrêt suivant]" déduit de l'étape
   suivante au lieu d'un "Marche" sec sans destination.
5. **Lien Google Maps cliquable dans le SMS, trajet pré-rempli** —
   implémenté avec le format d'URL universel
   (`google.com/maps/dir/?api=1&origin=...&destination=...&travelmode=transit`),
   aucun appel API supplémentaire ni coût : les coordonnées des deux
   arrêts sont déjà résolues pour l'appel à Google Routes lui-même.

Contrat `envoyer_sms_itineraire` et consigne de prompt (§4/§5 de la
spec) mis à jour en conséquence — nécessite de redéclarer le paramètre
`nom` côté outil ElevenLabs et de recoller la section "Itinéraire" du
prompt.

Vérifié en local : formatage du SMS avec nom/lien/durée de marche et
sans (dégradation propre dans tous les cas), migration de colonne
confirmée sur la base locale existante, lien Google Maps généré
correct. Suites `verifier_api.py` (7/8, échec réseau sandbox connu) et
`verifier_backoffice.py` (12/12) relancées sans régression.

**Reste à faire** : nouveau test d'appel une fois le paramètre `nom`
et la consigne de prompt mis à jour côté ElevenLabs.

## ✅ Fait le 12/10/2026 — outils déclarés côté ElevenLabs, consigne de prompt écrite, durée de marche ajoutée

Suite du premier test d'appel réel : l'agent ne trouvait pas d'itinéraire
complexe et proposait une mise en relation — cause identifiée, pas un bug
caché : `calculer_itineraire_complexe` et `envoyer_sms_itineraire`
n'avaient jamais été déclarés comme outils côté agent ElevenLabs (étape
manuelle systématique pour chaque nouvel outil de ce projet, jamais
automatique). Contrats complétés dans la spec (§4, champ `description`
manquant — essentiel pour qu'ElevenLabs sache quand les appeler — et
descriptions de paramètres détaillées), puis les deux outils déclarés
par l'utilisateur côté interface.

**Remarque de l'utilisateur en relisant le brouillon de consigne de
prompt, prise en compte** : annoncer une section de marche sans
indication de durée ("rejoignez l'arrêt...") est trop sec à l'oral —
contrairement à un horaire de bus, l'appelant n'a aucun repère pour
savoir si c'est 2 minutes ou 15. Problème trouvé en creusant : **la
donnée n'existait même pas** — le champ demandé à l'API Google
(`FIELD_MASK`) ne récupérait pas la durée de marche. Corrigé :
`routes.legs.steps.staticDuration` ajouté à la requête,
`itineraire_google.py` l'expose dans chaque étape (`duree_min`, jamais
à zéro par défaut si absente — CLAUDE.md, exactitude), répercuté dans
le SMS ("🚶 Marche, environ 4 min") et dans la consigne de prompt (§5,
section Itinéraire, maintenant stabilisée).

**Idée "quai opposé" (même remarque), pas construite** : à la
connaissance de Claude, l'API Google Routes ne descend pas à ce niveau
de détail (arrêt, pas numéro de quai) — pas de tentative d'implémentation,
question laissée ouverte si une vraie réponse Google contredit ça un jour.

**Angle produit noté par l'utilisateur, pas actionné** : le SMS
d'itinéraire, proposé comme un service réel (pas une simple formalité),
pourrait légitimer à terme la collecte d'un numéro pour recontacter un
appelant — contrairement à une demande de numéro "à froid", qui ne fait
pas sens hors contexte de service rendu. Rejoint le point déjà noté sur
le registre de consentement (actuellement un simple log succès/échec,
pas un opt-in structuré comme sur objets_perdus/demandes_rappel) — à
reprendre ensemble, pas aujourd'hui.

**SMS recadré comme un "récap" plutôt qu'un envoi systématique**, à la
demande de l'utilisateur : titre du SMS changé ("📋 Récap de votre
itinéraire TABM"), phrase de proposition orale changée en service
optionnel ("Si vous voulez, je peux vous envoyer un récap par SMS.").

Vérifié en local (formatage avec et sans durée de marche connue, suites
`verifier_api.py` 7/8 — démarrage à froid confirmé sans rapport, ré-essai
propre — et `verifier_backoffice.py` 12/12). **Pas encore retesté en
appel réel** avec les outils maintenant déclarés côté ElevenLabs — à
faire par l'utilisateur à la prochaine occasion.

## ✅ Fait le 12/10/2026 — premier envoi SMS réel réussi, bug de visibilité corrigé au passage

Premier test réel d'`envoyer_sms_itineraire` : aucun SMS reçu, et
surtout **aucune trace dans `sms_envoyes`** — silence total, aucun
moyen de diagnostiquer. Deux correctifs enchaînés :

1. Export CSV `sms_envoyes.csv` ajouté (`assistant/backoffice/
   exports.py`, même route que les exports existants), pour pouvoir
   consulter le résultat des tâches de fond sans accès à la base de
   production — manquait depuis le début, gap comblé dans l'urgence du
   diagnostic plutôt que découvert plus tard.
2. Cause racine du silence : le `try/except` d'`envoyer_sms_itineraire`
   n'attrapait que les erreurs réseau vers Google/Twilio, pas une
   exception imprévue ailleurs dans la fonction — une tâche de fond qui
   plante en dehors de ce périmètre ne laissait donc aucune trace.
   Élargi à toute exception. Vérifié en local en provoquant une vraie
   exception (heure mal formée) : désormais bien consignée au lieu de
   disparaître.

Après redéploiement : **premier SMS réel reçu avec succès**
(Émile Ripert → Mairie Sud), texte formaté conforme à ce qu'on avait
préparé ensemble (émojis par étape, correspondance visible, durée
totale), `succes:1` dans `sms_envoyes`. La chaîne complète fonctionne
de bout en bout : recalcul Google → formatage → envoi Twilio → journal.

**Reste à faire** : test en conditions réelles via un vrai appel
(Phase 2) — trajets suggérés : Émile Ripert (Velaux) → la Clinique de
Marignane (force le passage par le calculateur complexe, vérifié dans
le GTFS le 12/10), avec Mairie Sud (Vitrolles) → Mairie des
Pennes-Mirabeau et Clinique de Rognac → Clinique de Marignane en
solutions de repli.

## 💡 Idées back-office notées le 12/10/2026, pas prioritaires

Trois évolutions demandées par l'utilisateur, à reprendre ensemble plus
tard — pas d'action aujourd'hui :

1. **Outil de moyenne horaire des appels, à enrichir.** Courbes pour
   visualiser les pics horaires (heures pleines/creuses), peut-être
   ventilées par tranche de 15 min. Voir aussi comment l'intégrer
   proprement à la page (actuellement une simple tuile).
2. **Enrichir la base de connaissance "commercial" par des documents
   (PDF) injectés depuis le back-office**, en complément du site web
   scrapé. Point d'attention déjà identifié par l'utilisateur lui-même :
   gestion des conflits entre sources documentaires (site web vs PDF
   injecté sur le même sujet) — à trancher avant de construire quoi que
   ce soit, pas une simple question d'upload de fichier.
3. **Alerte d'expiration du GTFS visible directement dans le
   back-office**, pas seulement dans les logs de démarrage du serveur
   (actuellement : un message affiché uniquement au lancement de
   l'application, que l'équipe CRC ne voit jamais) — pour que les
   agents sachent qu'une mise à jour est nécessaire sans dépendre de
   Claude pour le leur signaler. Déclenché le 12/10 par une vraie
   alerte vue en local : GTFS actuel expirant le 18/10/2026, mais
   l'utilisateur confirme que ça reste acceptable en mode test tant que
   l'équipe réseau n'a pas publié de nouveau GTFS — pas une urgence.

## 🔶 En cours le 12/10/2026 — envoi SMS de l'itinéraire complexe (Twilio)

Suite directe de l'entrée du 08/10 ci-dessous : premier bout du "Graal"
évoqué par l'utilisateur (collecte vocale → itinéraire → SMS). Avant de
coder, deux questions ont été creusées avec l'utilisateur :

- **Risque de double calculateur, déjà traité le 08/10** (jamais
  `calculer_itineraire` et `calculer_itineraire_complexe` pour le même
  trajet) — confirmé que ce même principe s'applique au SMS : le texte
  envoyé est reconstruit côté serveur à partir d'un nouveau calcul,
  jamais composé par le LLM, pour ne jamais risquer un SMS qui
  contredit ce qui a été dit à l'oral.
- **Clarification technique importante** : l'utilisateur pensait que la
  bonne reconnaissance de lieux flous par Google Maps mobile venait
  d'une reconnaissance vocale supérieure — en réalité, chez nous la
  transcription est déjà faite par ElevenLabs en amont, donc le gain
  potentiel viendrait de l'**API Places** (interprétation d'un texte
  flou en lieu réel), pas de la Speech-to-Text. Idée notée pour plus
  tard (fallback quand `rechercher_arret` ET `rechercher_repere`
  échouent tous les deux), pas actionnée aujourd'hui.

**Implémenté et vérifié ce soir** :
- Numéro d'envoi Twilio (`+33939205690`) ajouté à `data/config.yaml`
  (paramètre du réseau, pas un secret). Identifiants
  (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`) ajoutés aux variables
  d'environnement Clever Cloud par l'utilisateur, jamais partagés dans
  la conversation.
- `assistant/outils/sms.py` : `formater_sms_itineraire` construit le
  texte (émojis par type d'étape — 🚶 marche, 🚌 bus, 🔄 correspondance
  — premier jet proposé par Claude, à affiner à l'usage) ;
  `envoyer_sms_itineraire` recalcule l'itinéraire via
  `calculer_itineraire_complexe`, formate, envoie via l'API REST Twilio
  (appel `httpx` direct, pas le SDK — cohérent avec le reste du projet),
  consigne toujours le résultat (succès ou échec) dans une nouvelle
  table `sms_envoyes`, ne lève jamais d'exception (cette fonction tourne
  en tâche de fond, après que l'appel ait déjà répondu à l'agent).
- Nouvelle route `/outils/envoyer_sms_itineraire`
  (`assistant/api/main.py`) : répond tout de suite (`accepte: true`),
  programme le recalcul + l'envoi réel via `BackgroundTasks` — pour ne
  jamais ajouter la latence d'un deuxième appel Google (400-600 ms déjà
  mesurés) ni celle de Twilio par-dessus au tour de parole en direct.
  Nouvel interrupteur back-office **indépendant** de
  `calculer_itineraire_complexe` (coût réel par SMS envoyé, niveau de
  confiance encore à établir), désactivé par défaut.
- Contrat documenté dans la spec (§4) ; consigne de prompt (demande du
  numéro, phrase de transition) volontairement laissée en brouillon,
  comme pour `calculer_itineraire_complexe`.
- Vérifié en local : formatage du texte correct sur un vrai résultat
  d'itinéraire ; conversion du numéro au format international (Twilio)
  correcte ; sans `GOOGLE_ROUTES_API_KEY`/Twilio configurés → la tâche
  de fond échoue proprement et consigne l'erreur dans `sms_envoyes`,
  jamais de plantage ; interrupteur désactivé par défaut (503), activé
  manuellement → fonctionne, réactivé à l'état désactivé après test ;
  téléphone invalide → 422. Suites `verifier_api.py` (7/8, échec réseau
  sandbox connu) et `verifier_backoffice.py` (12/12) relancées sans
  régression.

**Reste ouvert** :
- Le "registre des consentements" décrit dans la spec (§3, horodatage +
  formulation employée + extrait audio) n'existe pas réellement pour
  aucun outil aujourd'hui, `envoyer_sms_itineraire` y compris — seule
  une table de log simple (succès/échec + texte envoyé) existe. Écart
  déjà présent avant cette session pour `enregistrer_objet_perdu`/
  `demander_rappel`, pas quelque chose à résoudre uniquement pour le SMS.
- Pas de vrai test d'envoi (nécessite les identifiants Twilio réels,
  jamais présents dans cet environnement) — à faire par l'utilisateur,
  même méthode que les vérifications de production de cette semaine.
- Consigne de prompt toujours à stabiliser avec l'utilisateur.
- Idée API Places pour les lieux hors lexique, notée ci-dessus, pas
  commencée.

## ✅ Fait le 09/10/2026 — nouvel incident d'exposition d'`API_TOKEN`, rotation complète refaite

En voulant tester `calculer_itineraire_complexe` en production (voir
entrée du 08/10 juste en dessous), l'utilisateur a collé par
inadvertance une commande `curl` contenant le vrai `API_TOKEN` de
production en clair — plus sérieux que l'incident de la veille sur la
clé Google, puisqu'`API_TOKEN` protège l'ensemble des outils de l'API,
pas un seul usage restreint. Même réflexe appliqué immédiatement :
jeton considéré compromis, rotation complète aux 4 endroits où il vit
(même procédure qu'au 28/09) :
1. Variable d'environnement Clever Cloud.
2. En-tête `Authorization` des 9 outils déclarés côté agent ElevenLabs.
3. URL du webhook de fin d'appel (`?jeton=...`) — recréée (ElevenLabs
   ne permet pas de modifier l'URL d'un webhook existant, seulement
   d'en créer un nouveau puis de le sélectionner comme webhook actif).
4. En-tête `Authorization` du webhook de personnalisation (modifiable
   en place, contrairement au webhook post-appel).

**Deux erreurs en cours de route, aucune grave** : (a) confusion entre
la nouvelle valeur d'`API_TOKEN` et celle de `GOOGLE_ROUTES_API_KEY`
lors d'un copier-coller — mauvaise valeur déployée sur Clever Cloud
puis sur le webhook de fin d'appel, corrigée dès détection (401
persistant après un premier redéploiement, qui a mis la puce à
l'oreille) ; (b) une URL de webhook malformée en collant le jeton
directement dans la commande curl — résolu en reprenant la méthode
`read -s` déjà utilisée pour la clé Google (le jeton ne transite plus
jamais en clair dans une commande affichée à l'écran).

**Vérifié de bout en bout** : `curl` direct sur `/outils/transferer_agent`
et sur le webhook `/webhooks/elevenlabs/fin_appel` avec le nouveau
jeton → 200 dans les deux cas. Puis un vrai appel test côté ElevenLabs
(widget) confirmé fonctionnel par l'utilisateur — seule vérification
qui garantit que les 9 outils et les deux webhooks envoient bien le bon
jeton tel que configuré côté interface, pas seulement notre propre
serveur.

**Point à reprendre froidement, hors urgence** : deux incidents de ce
type coup sur coup (08/10 et 09/10) suggèrent que le geste "coller une
commande curl complète sans la nettoyer d'abord" est un piège facile à
reproduire, pas un simple coup de malchance. À voir avec l'utilisateur
si une consigne plus systématique (ex. toujours utiliser `read -s`
d'emblée pour tout test impliquant un secret, plutôt qu'en rattrapage
après coup) vaut la peine d'être actée une fois pour toutes.

## 🔶 En cours le 08/10/2026 — calculateur d'itinéraire Google Routes API, mise en place en cours

Contexte : l'utilisateur a vérifié manuellement que le réseau TABM/Métropole
Mobilité est bien couvert par les données transit de Google (itinéraire
réel retrouvé pour un trajet déjà testé avec notre moteur maison,
résultats cohérents). Objectif : utiliser l'API Routes de Google
(`travelMode: TRANSIT`) en complément ou en remplacement de
`assistant/outils/itineraire.py`, avec notre moteur gardé en secours.
S'inscrit dans une vision plus large de l'utilisateur ("le Graal") :
collecte vocale du point de départ/arrivée → calcul d'itinéraire → envoi
du résumé par SMS (Twilio, fil encore ouvert séparément).

**Recherche tarifaire faite (web, accès direct à developers.google.com
bloqué depuis cet environnement)** : le crédit de 200$/mois a disparu le
1er mars 2025, remplacé par un quota gratuit mensuel par type d'appel
facturé (SKU) : env. 10 000 appels gratuits/mois en SKU "Essentials",
5 000 en "Pro". Pas pu confirmer avec certitude dans quel SKU tombe une
requête `travelMode: TRANSIT` (aucune source trouvée ne le précise
explicitement) — hypothèse raisonnable : Essentials, à vérifier
réellement une fois la clé créée (regarder le SKU facturé dans la
console après quelques appels de test).

**Mise en place démarrée, pas-à-pas avec l'utilisateur, projet Google
Cloud `assistant-vocal-crc-poc`** :
- Projet créé, API Routes activée (seule — pas "toutes les API Maps",
  pour limiter la surface).
- Clé API créée et restreinte : "Restrictions relatives aux API" → Routes
  API uniquement (confirmé sur capture d'écran). Restriction par adresse
  IP volontairement laissée de côté pour l'instant (pas de confirmation
  qu'une IP sortante fixe existe côté Clever Cloud pour cette app — à
  creuser plus tard, non bloquant).
- Bonus trouvé en cours de route : le projet bénéficie aussi d'un crédit
  d'essai Google Cloud classique (264 €, jusqu'au 7 janvier 2027,
  facturation nulle pendant l'essai) — indépendant du quota gratuit par
  SKU, marge de sécurité supplémentaire pour tout le POC.

**Non résolu ce soir** : la création de l'alerte de budget (page
"Facturation" du compte, pas celle de Maps Platform) a échoué avec une
erreur générique côté console Google ("Une erreur s'est produite lors de
la création des alertes budgétaires"), même après un nouvel essai. Pas
bloquant (le quota gratuit + le crédit d'essai protègent déjà d'une
mauvaise surprise), mais **à reprendre à la prochaine session** : retenter
la création de l'alerte budgétaire (ex. 5€/mois) depuis
console.cloud.google.com → Facturation → Budgets et alertes.

**Pas encore fait** : récupération de la valeur de la clé (jamais collée
dans la conversation, par principe — même leçon que la rotation
d'`API_TOKEN`), ajout à `.env` et aux variables d'environnement Clever
Cloud, mesure de la latence réelle de `computeRoutes` depuis
l'environnement de déploiement (point potentiellement bloquant : budget
de 300 ms/endpoint non négociable de `CLAUDE.md`, un appel réseau externe
est moins prévisible que notre SQLite local — à chiffrer avant de décider
si Google passe en tentative bloquante ou reste cantonné à un usage hors
chemin critique), et code d'intégration (nouvelle fonction avec repli
automatique vers `calculer_itineraire()` existant en cas d'erreur/absence
de résultat).

**Idée notée en explorant les API Google, pas actionnée** : des API
météo et pollen existent aussi sur la même plateforme — pourrait à terme
permettre de proposer un itinéraire privilégiant moins de marche en cas
de pluie (axe "weather-aware" déjà évoqué par l'utilisateur dans sa
vision du Graal). Après le calculateur d'itinéraire et le SMS, pas avant.

**⚠️ Incident mineur, même famille que celui d'`API_TOKEN` le 28/09** : en
testant la latence réelle de l'API Google (via Cloud Shell, pour éviter
de donner la clé à Claude — voir plus haut), l'utilisateur a collé par
inadvertance la commande `curl` complète dans la conversation, clé en
clair incluse. Clé restreinte à l'API Routes uniquement (pas de risque
sur le reste du compte Google Cloud), mais régénérée par réflexe
immédiatement ("rotation de la clé" côté console Google, nouvelle valeur
mise à jour dans Clever Cloud). Aucun usage frauduleux constaté dans la
fenêtre d'exposition (quelques minutes). Même leçon qu'avant : toute
commande de test contenant un secret doit être nettoyée avant d'être
partagée, pas seulement "ne jamais coller la clé elle-même" — la
consigne donnée à l'utilisateur sera reformulée pour le dire plus
explicitement la prochaine fois.

**Latence réelle mesurée après régénération de la clé** (toujours depuis
Cloud Shell, donc optimiste) : **168 ms**, avec un vrai trajet trouvé
(correspondance ligne 12 → ZEN A, 56 min) — différent de celui vérifié
manuellement plus tôt sur Google Maps, normal (heure de la journée
différente, offre de bus différente). Prouve au passage que Google
recalcule bien selon l'horaire réel transmis, pas une réponse figée.
Au passage, découvert que l'activation initiale de l'API Routes n'avait
en fait jamais abouti (clé créée, mais le service lui-même absent de la
liste "API et services activés") — ré-activée correctement cette fois,
vérifiée présente avec un bouton "Disable" (pas "Enable").

**Décision de conception importante, actée avec l'utilisateur** : risque
identifié par l'utilisateur lui-même — avoir deux calculateurs (maison et
Google) risquait de donner deux réponses différentes pour un même trajet
selon lequel répond, ce qui casserait la confiance plus sûrement qu'une
réponse simple mais cohérente. Règle retenue, qui élimine le risque
structurellement plutôt que de le gérer après coup :
- `calculer_itineraire` (moteur maison, GTFS) reste **le seul** utilisé
  pour les trajets qu'il sait couvrir (direct ou une correspondance,
  sans marche).
- `calculer_itineraire_complexe` (nouveau, Google) n'est appelé **qu'en
  repli**, uniquement quand le premier renvoie `trouve: false` — jamais
  les deux pour le même trajet. Dans ce cas, l'agent pourra restituer le
  trajet Google à l'oral, puis proposer un SMS récapitulatif (futur, lié
  au fil Twilio SMS — l'outil d'envoi n'existe pas encore).
- Nouvel interrupteur back-office **indépendant** de celui de
  `calculer_itineraire` — l'utilisateur veut explicitement pouvoir garder
  la main dessus séparément, y compris le suspendre pendant le POC le
  temps de plus de tests, sans toucher au calculateur maison.

**Implémenté et vérifié ce soir** :
- `assistant/outils/itineraire_google.py` : nouvelle fonction
  `calculer_itineraire_complexe`, résout les coordonnées des arrêts via
  `charger_arrets_logiques` (déjà en place), appelle l'API Google
  (timeout 4s — généreux par rapport au budget de 300 ms de CLAUDE.md,
  assumé pour ce repli explicitement hors chemin critique habituel, **à
  resserrer une fois une vraie mesure faite depuis Clever Cloud**, pas
  seulement Cloud Shell). `GOOGLE_ROUTES_API_KEY` absente → dégradation
  gracieuse (`trouve: false`), jamais de plantage — un réseau dupliqué
  sans cette clé doit continuer à fonctionner (CLAUDE.md, paramétrage).
- Nouveaux schémas Pydantic (`ItineraireComplexeRequete/Reponse`,
  `assistant/api/schemas.py`) — étapes typées `marche`/`transport`,
  volontairement plus génériques que le format existant (celui-ci ne
  gère que direct/une correspondance, insuffisant pour ce que Google peut
  renvoyer).
- Nouvelle route `/outils/calculer_itineraire_complexe`
  (`assistant/api/main.py`), nouvel interrupteur
  `calculer_itineraire_complexe` dans `NOMS_OUTILS`/
  `_OUTILS_INACTIFS_PAR_DEFAUT` (`assistant/outils/db.py`) — désactivé
  par défaut comme `calculer_itineraire`, libellés back-office ajoutés
  (`assistant/backoffice/page.py`).
- Contrat de l'outil documenté dans la spec (§4) — **la consigne de
  prompt (§5) n'est volontairement pas encore rédigée**, l'utilisateur a
  explicitement dit qu'il faudra la retravailler ensemble avant
  d'activer ce bouton en vrai.
- Vérifié en local : sans clé → réponse propre `trouve: false` (pas de
  500) ; avec une fausse clé → vrai appel réseau à Google, refusé
  proprement, pas de plantage ; interrupteur désactivé par défaut (503) ;
  activé manuellement → fonctionne ; réactivé à l'état désactivé par
  défaut à la fin du test. Suites `verifier_api.py` (7/8, échec réseau
  sandbox connu, sans rapport) et `verifier_backoffice.py` (12/12)
  relancées sans régression.

**Mesure de latence réelle faite le 09/10/2026** (après l'incident de
rotation d'`API_TOKEN` ci-dessus) : deux appels réels en production,
619 ms puis 436 ms — largement au-dessus des 300 ms, de façon
constante sur deux mesures indépendantes, pas un accident ponctuel.
**Confirme que la décision de conception (Google jamais en tentative
live bloquante, uniquement en repli explicite) était la bonne** — un
timeout de 4s reste raisonnable pour ce repli assumé hors chemin
critique. Question fermée.

**Reste ouvert, volontairement pas traité ce soir** :
- L'outil d'envoi de SMS (Twilio) n'existe pas du tout encore — sans lui,
  `calculer_itineraire_complexe` peut répondre à l'oral mais pas encore
  tenir la promesse "je vous l'envoie par SMS".
- La consigne de prompt pour ce cas (§5 de la spec) reste à écrire avec
  l'utilisateur.
- Décision produit encore ouverte : l'utilisateur envisage de laisser ce
  bouton suspendu pendant le POC le temps d'accumuler plus de tests,
  avant de l'activer en situation réelle d'appel.
- Alerte de budget Google Cloud toujours pas créée (voir plus haut).

## ✅ Fait le 28/09/2026 — dossier d'audit DSI démarré, rotation du jeton API, rétention ElevenLabs corrigée

Contexte : le POC a passé le test interne et pourrait devenir un pilote
public sur une filiale — préparation d'un dossier d'audit exhaustif pour
la DSI (`docs/audit-dsi.md`, parties 2 et 3 rédigées : architecture,
choix techniques, inventaire des outils). Deux failles de sécurité/RGPD
trouvées en le rédigeant, corrigées le jour même :

- **Rétention ElevenLabs non configurée** : `deletion_time_unix_secs`
  était `null` sur tous les appels (rétention illimitée par défaut,
  2 ans selon leur documentation), alors que l'audio et la transcription
  de chaque appel sont conservés. Corrigé côté utilisateur : mode de
  confidentialité de l'agent, rétention à 365 jours, suppression
  automatique de la transcription/PII et de l'audio après ce délai,
  appliqué rétroactivement aux conversations existantes. Vérifié sur un
  appel réel après coup : `deletion_time_unix_secs` renseigné,
  `delete_transcript_and_pii: true`, `delete_audio: true`.
- **Jeton API (`API_TOKEN`) exposé en clair** dans plusieurs charges de
  webhook collées dans les échanges de la session — donc dans
  l'historique de conversation. Rotation effectuée aux 4 endroits qui en
  dépendent : variable d'environnement Clever Cloud, en-tête
  `Authorization` des 9 outils ElevenLabs, URL du webhook de fin d'appel
  (`?jeton=...`), en-tête du webhook de personnalisation. Un premier
  test a échoué (appel raccroché aussitôt) — cause : le nouveau réglage
  du webhook de personnalisation avait été modifié mais pas publié côté
  ElevenLabs. Une fois publié, testé et vérifié sur un appel réel :
  les 3 outils appelés montrent bien le nouveau jeton dans leurs
  en-têtes, le webhook de fin d'appel est bien reçu, les variables
  dynamiques de personnalisation sont bien renseignées.

**Reste ouvert, à faire à l'occasion (pas urgent)** :
- `data/config.yaml` est versionné par git (pas ignoré, contrairement à
  ce que dit `CLAUDE.md`) et contient une clé API Mecatran en clair,
  présente dans l'historique depuis plusieurs commits — à régénérer
  auprès de Mecatran/la Métropole Mobilité, et corriger la description
  du `.gitignore` dans `CLAUDE.md`.
- Vérifier la signature HMAC du webhook de fin d'appel plutôt que de ne
  compter que sur le jeton dans l'URL (secret HMAC déjà généré côté
  ElevenLabs à la recréation du webhook, non utilisé pour l'instant côté
  code).
- Suite du dossier d'audit : parties 1 (intention/genèse), 4 (code
  source), 7 (traçabilité), annexes (5 et 6 rédigées, voir entrée
  suivante).

## ✅ Fait le 29/09/2026 — mot de passe back-office séparé du jeton API

En relisant les parties 5/6 du dossier d'audit, l'utilisateur a
identifié la recommandation « séparer le mot de passe back-office du
jeton des outils » comme non négociable, pas une amélioration future :
`API_TOKEN` circule par construction dans des endroits bien moins
protégés (en-têtes ElevenLabs, URL de webhook, captures d'écran) —
le compromettre aurait donné accès à jusqu'à 90 jours de transcripts
d'appels via le back-office.

Corrigé : nouvelle variable `BACKOFFICE_MOT_DE_PASSE`, choisie
librement par l'utilisateur, indépendante d'`API_TOKEN`
(`assistant/api/auth.py`). Démarrage de l'application bloqué si
absente, même principe qu'`API_TOKEN`. `tests/verifier_backoffice.py`
mis à jour pour l'utiliser. Vérifié en local : l'ancien jeton API ne
fonctionne plus comme mot de passe back-office (401), le nouveau mot
de passe dédié fonctionne (200), suites de vérification API et
back-office toutes deux relancées avec succès.

**Reste à faire côté utilisateur** : choisir la vraie valeur de
`BACKOFFICE_MOT_DE_PASSE` et l'ajouter aux variables d'environnement
Clever Cloud (aucun réglage ElevenLabs concerné cette fois, contrairement
à la rotation du jeton API — ce mot de passe n'est utilisé nulle part
côté ElevenLabs), puis fusionner vers `main` pour déployer.

## ✅ Fait le 29/09/2026 — parties 5/6 du dossier d'audit + purge automatique des transcripts d'appel

En rédigeant la partie 6 (RGPD) du dossier d'audit, constat plus grave
que celui d'ElevenLabs la veille : notre propre base de données
(`appels.donnees_brutes`) conservait la charge JSON complète de chaque
appel — transcript intégral, numéro de l'appelant — **indéfiniment,
sans aucune fonction de suppression dans tout le code** (vérifié
explicitement). Corriger ElevenLabs ne suffisait donc pas.

Décidé avec l'utilisateur : purge automatique de `donnees_brutes`
après 90 jours (compromis entre suivi qualité à chaud et minimisation),
sans toucher à la ligne ni aux métriques déjà extraites (`duree_secs`,
`cout_usd`, `minutes_asr`/`tts`, `modeles_llm`, `tokens_llm`...), qui
doivent rester disponibles indéfiniment (CLAUDE.md, traçabilité — ce
ne sont pas des données personnelles). Implémenté :
`purger_transcripts_expires()` dans `assistant/backoffice/appels.py`,
déclenchée au démarrage de l'application puis une fois par jour
(boucle asyncio dans le nouveau `lifespan` de `assistant/api/main.py`
— pas de nouvelle dépendance, pas de planificateur externe).

Effet de bord trouvé et corrigé au passage : `retraiter_tracabilite`
(qui recalcule les métriques à partir de `donnees_brutes`) aurait
écrasé les métriques déjà valides d'un appel purgé avec des valeurs
vides si on la relançait après coup — garde-fou ajouté (elle ignore
maintenant les lignes déjà purgées).

Vérifié en local avant commit : un appel vieux de 100 jours voit son
contenu vidé, un appel récent reste intact, un `retraiter_tracabilite`
après purge laisse les métriques de l'appel purgé inchangées. Suites
de vérification API (7/8, échec réseau sandbox connu, sans rapport)
et back-office (12/12) toutes deux relancées avec succès.

**Reste ouvert** :
- `objets_perdus` / `demandes_rappel` : pas de politique de rétention.
  Contrairement au transcript d'appel, ces données restent utiles tant
  que la demande n'est pas résolue — décision produit à prendre avec
  l'utilisateur (combien de temps après résolution ? y a-t-il un
  signal de résolution fiable pour objets_perdus, qui n'a pas de champ
  "traité" contrairement à demandes_rappel ?), pas une simple durée
  technique.
- Tout le reste listé dans l'entrée du 28/09 (clé Mecatran, HMAC,
  parties 1/4/7 du dossier) reste d'actualité.

## 🔶 En cours le 25/09 (soir) — comparaison de LLM avant migration, PAS TRANCHÉ

Contexte : ElevenLabs a averti que Gemini 2.5 Flash (modèle actuel) sera
obsolète le 30/11/2026, migration automatique sinon. Décision de ne pas
attendre et de comparer plusieurs candidats avant de choisir, plutôt que
de prendre le remplaçant par défaut à l'aveugle.

**Candidats testés ce soir, en appel réel** (3 webhooks analysés en
détail) : Gemini 3.5 Flash-Lite (deux appels) et Qwen3.5-397B-A17B (un
appel, hébergé par ElevenLabs, "idéal pour un cas d'utilisation
agentique" selon leur fiche).

**Aucun des deux n'est prêt à déployer tel quel** — chacun a un vrai
défaut, pas juste une question de goût :

- **Gemini 3.5 Flash-Lite** : silences de 7 à 12 secondes avant que le
  tour ne démarre (`convai_turn_silence_before_initiation`), alors que
  le LLM lui-même répond vite (~0,5-0,7s) — cause non identifiée,
  semble être un problème de tour de parole/VAD, pas le modèle. **Bug
  plus grave** trouvé dans un appel de démo : a tenté de soumettre
  `enregistrer_objet_perdu` avec des valeurs inventées (`"nom":
  "inconnu"`, `"telephone": "inconnu"`) avant même d'avoir posé les
  questions correspondantes à l'appelant — bloqué par chance seulement
  parce que le champ `lieu` avait une valeur hors énumération. Dans le
  même appel : a inventé une fausse contrainte ("nous ne pouvons plus
  traiter de nouvelle demande sur cet appel") pour refuser une demande
  d'itinéraire qu'il avait pourtant très bien traitée plus tôt dans le
  même appel.
- **Qwen3.5-397B-A17B** : a appelé `rechercher_repere` au lieu de
  `rechercher_arret` pour un vrai nom d'arrêt ("Bastide Blanche"), et a
  cherché une destination en supposant silencieusement qu'elle était
  dans la même commune que le départ (sans le demander) — résultat, un
  mauvais arrêt confirmé à l'appelant sans qu'il puisse le savoir.
  Coût réel mesuré ~3x plus élevé que Gemini 3.5 Flash-Lite sur un
  appel comparable (`llm_price` 0,062 $ contre 0,020 $), malgré un
  prix/minute affiché plus bas — parce que Qwen ne bénéficie d'aucun
  cache de contexte d'un tour à l'autre (`input_cache_read` toujours à
  0), contrairement à Gemini.

**Confirmé au passage** : la config "LLM de secours" reste sur Gemini
2.5 Flash (l'obsolète) quel que soit le modèle principal choisi — un
repli vers ce modèle a été observé dans les deux séries de tests. À
corriger indépendamment du choix final.

**Pas fait ce soir** : aucun modèle changé en production, aucune
décision prise. On s'est arrêtés volontairement plutôt que de choisir
sous pression du calendrier de dépréciation (30/11, large marge).

### À faire la semaine prochaine

1. Corriger la config "LLM de secours" côté ElevenLabs (ne doit plus
   pointer vers Gemini 2.5 Flash).
2. Retester spécifiquement le parcours `enregistrer_objet_perdu` (point
   le plus sérieux trouvé ce soir) sur chaque candidat avant toute
   décision — c'est le genre de bug à exclure formellement avant un
   déploiement réel, pas à ignorer parce qu'il ne s'est produit qu'une
   fois.
3. Chercher la cause des silences de 7-12s sur Gemini 3.5 Flash-Lite
   (tour de parole/VAD ?) avant de l'écarter ou de le retenir — non
   élucidé ce soir.
4. Éventuellement tester un 3e candidat (Gemini 3.1 Flash Lite avait
   été identifié comme alternative proche, moins cher, meilleur pire
   cas de latence affiché — mais génération antérieure, pas encore
   testé du tout).
5. Objectif : trancher avant le 30/11, mais pas dans la précipitation —
   les deux bugs les plus sérieux de ce soir (données inventées, fausse
   excuse de refus) sont exactement le genre de chose que ce projet
   s'est donné pour règle de ne jamais laisser passer.

## ✅ Fait le 25/09 — calculateur d'itinéraire, v0 expérimentale

Exploration approfondie avant de coder (voir aussi la discussion du
même jour) : API Cityway (aucun endpoint d'itinéraire exposé), Navitia/
Hove (racheté, accès désormais commercial, pas de portail développeur
libre-service confirmé), l'appel AJAX interne de plan.lametropolemobilite.fr
(trouvé via les outils de développement du navigateur, mais renvoie du
HTML non documenté, dépendant d'une session — pas fiable), OpenTripPlanner
(faisable sans Docker mais Java 25 + 2 Go de RAM par défaut rien que pour
une zone de cette taille, coût comparable à la question mpnet déjà tranchée
le 04/09). Décision : moteur maison, dans la stack actuelle.

**Construit** :
- `data/reperes.yaml` : une mairie par commune (8), coordonnées vérifiées
  une par une via l'API Adresse du gouvernement (jamais estimées). Piège
  rencontré : une recherche par nom de commune seul est tombée sur
  "Vitrolles-en-Luberon" (Vaucluse) au lieu de Vitrolles (Bouches-du-Rhône)
  — toujours vérifier le département.
- `assistant/outils/reperes.py` : résout un repère cité en clair ("la
  mairie") vers l'arrêt le plus proche (distance à vol d'oiseau).
- `assistant/outils/itineraire.py` : trajet direct ou une correspondance
  maximum, recherche bornée aux prochains départs (pas toute la
  journée) — pas un vrai moteur RAPTOR, suffisant pour ce réseau.
  Testé sur des cas réels tirés du GTFS (trajets directs et
  correspondances trouvés avec des délais cohérents, et correctement
  aucun résultat quand aucun trajet n'existe dans la fenêtre cherchée).
- Deux nouveaux outils (`rechercher_repere`, `calculer_itineraire`),
  **désactivés par défaut** dans le back-office (case "Recherche
  d'itinéraire", décision explicite de l'utilisateur pour ne pas
  fragiliser les démos actuelles) — activables en un clic, sans
  redéploiement.

**Bug corrigé en cours de route** : `trouver_par_stop_id` (déjà
existant) recharge tout l'index des arrêts à chaque appel — appelé en
boucle dans la recherche de correspondance, ça aurait explosé le budget
de 300 ms. Corrigé en construisant l'index une seule fois par requête.

**Reste à faire côté utilisateur** avant d'activer en vrai : recopier
le contrat des deux outils (spec §4) et la section "Itinéraire" du
prompt (spec §5) dans ElevenLabs — pas fait automatiquement, comme pour
les autres outils.

**Pas fait** (périmètre volontairement limité pour ce premier test) :
- Plus d'une correspondance.
- Repères autres que les mairies (gares, écoles, hôpitaux...).
- Le fichier `.env` local a été perdu deux fois pendant cette session
  suite à des reprises après inactivité — comportement normal (jamais
  commité), mais à garder en tête : après une longue pause, relancer le
  serveur en local nécessite de recréer `.env`.

## ✅ Fait le 08/09 (soir) — tests en appel réel du rappel proactif + ASR

Suite à la mise en prod du rappel proactif abonnement/vélo (voir juste en
dessous), tests par appel téléphonique réel :

- **Bug trouvé et corrigé** : le premier test échouait avec "problème
  technique" au moment d'enregistrer le rappel motif "abonnement". Cause :
  la définition de l'outil `demander_rappel` dans la console ElevenLabs a
  sa propre liste de valeurs autorisées pour `motif` (séparée du prompt),
  qui n'avait pas été mise à jour. Corrigé côté ElevenLabs (ajout de
  `abonnement` et `velo` à la liste). **À garder en tête pour toute
  évolution future des motifs** : toujours mettre à jour 2 endroits côté
  ElevenLabs (le prompt ET la définition de l'outil), pas seulement notre
  code.
- Une fois corrigé, le parcours complet fonctionne (proposition proactive,
  collecte prénom/nom/téléphone, résumé).
- **Bug trouvé, pas corrigé** : "Combien coûte un abonnement mensuel ?"
  suivi de "pour un adulte ?" fait répondre l'assistant avec les tarifs
  enfant puis senior, avant de dire qu'il n'a pas l'info pour 43 ans.
  Recherche documentaire qui ne retrouve pas la bonne fiche tarif pour
  "adulte" — même famille de problème que les autres cas de retrieval déjà
  documentés dans ce fichier. Pas traité ce soir.
- Fausse alerte "bonne journée" au lieu de "bonne soirée" à 18h :
  `/webhooks/elevenlabs/personnalisation` renvoie la bonne valeur côté
  serveur (vérifié), et aucune occurrence de "bonne journée" en dur
  trouvée dans le prompt ElevenLabs. Cause non identifiée, non
  reproduite depuis — laissé de côté, à surveiller si ça revient.
- **ASR / termes de domaine** : test sur 3 arrêts piégeux (Pinchinades,
  Jas de Rhodes, Estroublans) dits naturellement, jamais épelés — les 3
  reconnus correctement, y compris Estroublans qui a 2 arrêts homonymes
  (désambiguïsation par commune réussie). Les termes de boost ASR
  semblent donc bien en place et efficaces.

## Punch-list déploiement réseau réel (à mener, pas commencé)

Discuté le 08/09 en fin de session — ce que l'utilisateur devra avoir en
tête pour un déploiement sur le vrai réseau, au-delà du POC actuel :

1. **Téléphonie / routage — le plus structurant.**
   - Comprendre l'existant : comment un appel arrive aujourd'hui à un
     agent CRC (standard, logiciel de centre d'appels, postes directs) ?
   - Horaires d'ouverture réels du CRC à préciser en config (aujourd'hui
     approximatifs dans le prompt).
   - "CRC ouvert/fermé" n'est vérifié par rien aujourd'hui — c'est le
     modèle qui devine d'après le prompt, sans horloge réelle. À calculer
     côté serveur et exposer en variable dynamique, comme
     `{{formule_cloture}}`.
   - `transferer_agent` ne fait que logger l'intention en base
     aujourd'hui — aucune vraie téléphonie. Il faudra un vrai mécanisme
     de transfert (SIP/Twilio) vers le standard CRC.
   - Débordement (bot activé quand les lignes humaines sont occupées) :
     probablement une intégration avec le système d'appels existant du
     CRC, pas juste une config Twilio.
   - Numéro Twilio français définitif — à confirmer où ça en est.
2. **Bouton on/off à clarifier puis connecter.** Aujourd'hui il ne coupe
   que nos outils back-end, pas la réponse au téléphone (ElevenLabs
   répond indépendamment). Distinguer avant de coder : arrêt d'urgence
   (coupe tout) vs bascule horaires automatique (CRC ouvert/fermé, point
   1) — probablement deux mécanismes différents.
3. **Sécurité**, déjà identifié dans ce fichier (section D) : signature
   HMAC des webhooks ElevenLabs, régénération de `API_TOKEN`, revoir
   l'authentification back-office avant de vraies données de voyageurs.
4. **Robustesse à l'échelle** : appels en parallèle (SQLite en écriture
   concurrente, tester en charge, WAL si besoin) ; fenêtre
   d'indisponibilité au déploiement (le GTFS se retélécharge à chaque
   déploiement, pas instantané).
5. **Qualité du contenu en continu** : cycle mesure-ajustement permanent,
   pas un sujet qu'on referme (cf. bug tarif abonnement adulte ce soir).
6. **Petits reliquats** : adresse email du pied de page (placeholder
   accepté pour l'instant), créneau horaire préféré pour le rappel (idée
   notée, pas implémentée), badge de rappel traité (dash neutre au lieu
   du vert initialement demandé, pas encore tranché).

## ✅ Fait le 08/09 — rappel proactif abonnement/vélo, prénom+nom

Deux nouveaux motifs de rappel ajoutés (`abonnement`, `velo`), synchronisés
dans `assistant/outils/rappels.py`, `assistant/api/schemas.py` et
`_NOMS_MOTIFS` (back-office). Spec (§4 et §5) mise à jour : le prompt
propose désormais un rappel proactif quand l'appelant veut *souscrire* un
abonnement (pas juste en connaître le tarif — ce cas reste répondu
normalement via rechercher_information), et après une réponse sur le
vélo en libre-service. Toute demande de rappel recueille maintenant
prénom + nom (pas de nouvelle colonne en base : les deux sont stockés
dans le champ `nom` existant, ex. "Marie Dupont" — une séparation en deux
colonnes n'apportait rien de plus pour l'usage actuel, rappeler quelqu'un
en le nommant correctement).

**Reste à faire côté utilisateur** : recopier les nouvelles sections
"Abonnement" et "Vélo en libre-service" du prompt système (spec §5) dans
la configuration de l'agent ElevenLabs — ce fichier ne les y pousse pas
automatiquement.

Idée notée pour plus tard, pas implémentée (proposée par l'utilisateur,
volontairement différée) : demander à l'appelant un créneau de
disponibilité préféré pour le rappel, à stocker et afficher au conseiller.
Nécessiterait une vraie colonne en base le jour où on s'y attaque.

## ✅ Fait le 08/09 — question du modèle d'embeddings tranchée

Test de qualité du candidat français (`antoinelouis/biencoder-distilcamembert-mmarcoFR`,
mesuré la semaine dernière comme meilleur compromis poids/latence que
mpnet) : réindexation isolée du corpus existant avec ce modèle (script
temporaire, hors du dépôt, ne touche à rien de production), même jeu de
54 questions, même logique de score/véto que `rechercher_information.py`.

**Résultat : aucun gain net.** Rappel top-5 50/54 (93% contre 94%
actuellement), réponse outil 39/54 (72% contre 74%), pièges inchangés
(1/8). Le candidat corrige 3 cas connus (dépositaires-agréés, courrier,
Rognac) mais en casse 5 autres qui fonctionnaient bien avec le modèle
actuel (étudiants, fauteuil roulant LeBus+, vélo, réclamation
ponctualité, transports scolaires) — un déplacement du problème, pas une
amélioration. Le cas "amendes" (collision "Comment payer...") échoue
avec les deux modèles : ce n'est pas une faiblesse propre à MiniLM.

**Décision : on reste sur le modèle actuel**, patché au fil de l'eau. Ni
le budget récurrent (32-76€/mois selon le palier Clever Cloud
nécessaire) ni l'effort d'ingénierie (dépendance PyTorch permanente ou
conversion ONNX) ne sont justifiés par un gain qui n'existe pas sur ce
candidat précis. Referme la question ouverte depuis le 04/09 — à
rouvrir uniquement si un autre candidat sérieux émerge.

## ✅ Fait le 04-08/09 — nettoyage du corpus, index recommité, vérifié en prod

`data/corpus_index.json` régénéré et commité (nettoyage du pied de page +
synonyme "abonnement", puis "billet"/"titre de transport" ajouté le 07/09).
Vérifié en production par curl le 08/09 : les deux formulations tarifs
répondent correctement.

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
