# Assistant vocal CRC — Spécification v0 (révisée)

**Nature** : démonstrateur autonome, sans intégration SVI. Sert à produire la matière du cahier des charges du pilote.
**Périmètre géographique** : zone Étang (Vitrolles, Marignane, Rognac, Berre-l'Étang, Velaux, Saint-Victoret, Gignac-la-Nerthe, Les Pennes-Mirabeau)
**Principe de priorisation** : statique d'abord, dynamique ensuite.

---

## 1. Périmètre fonctionnel

| Bloc | Motifs couverts | Part estimée du volume | Dépendance technique |
|---|---|---|---|
| **A — Commercial et pratique** | tarifs, abonnements, agences, conditions de transport, VLS le cas échéant | ~20-37 % | corpus documentaire |
| **B — Horaires théoriques** | premier/dernier bus, jours de circulation, horaire de passage, quelle ligne dessert quoi | ~30 % | GTFS statique |
| **C — Objets perdus** | qualification complète + coordonnées | ~14 % | aucune |
| **D — Sorties** | amendes, réclamations, TAD, scolaire, demande d'agent | ~12 % | aucune |
| *v1 — Temps réel* | *prochain passage réel, perturbations* | *reste* | *SIRI, GTFS-RT* |

Le bloc C est le premier à construire : il ne dépend de rien, il représente le gain organisationnel le plus net, et c'est le seul contexte où la collecte de coordonnées est attendue par l'appelant lui-même.

## 2. Deux régimes de fonctionnement

L'assistant se comporte différemment selon l'heure, et c'est le cœur de la démonstration.

**CRC ouvert** — la sortie par défaut est le transfert vers un agent.

**CRC fermé** (l'essentiel des heures de service du réseau) — aucun transfert possible. La sortie par défaut devient la demande de rappel, avec collecte de coordonnées. C'est le régime qui produit le plus de valeur : ces appels, aujourd'hui, ne produisent rien.

Les horaires d'ouverture sont un paramètre de configuration, pas une valeur en dur.

---

## 3. Ce que charge la couche données

| Table | Source | Rafraîchissement |
|---|---|---|
| `documents` | pages discursives du site du réseau | hebdomadaire |
| `arrets` + `arrets_phonetique` | `stops.txt` du GTFS `mamp-bde` | quotidien |
| `lignes` | `routes.txt` | quotidien |
| `passages_theoriques` | `stop_times.txt`, `calendar`, `calendar_dates` | quotidien |
| *`passages_temps_reel`* | *SIRI `BDE_URB`* | *v1* |
| *`perturbations`* | *GTFS-RT Service Alerts* | *v1* |

**Alerte à câbler** : le GTFS `mamp-bde` expire le 30/08/2026. Le job quotidien doit alerter si la validité se termine dans moins de 7 jours.

### Corpus documentaire (bloc A)

Environ 30 pages à extraire du site, **hors fiches horaires PDF** qui ne doivent jamais entrer dans l'index : tarifs et titres, conditions de vente, agences et points de vente, conditions de transport, accessibilité, TAD (conditions, pas réservation), objets trouvés (procédure), amendes (procédure), VLS le cas échéant.

Chaque document porte : source, URL, date d'extraction. L'agent doit pouvoir dire d'où vient une information et quand elle a été mise à jour.

### Paramétrage par réseau

Tout ce qui est propre à l'Étang vit dans un fichier de configuration : identité vocale, horaires d'ouverture, périmètre géographique, source GTFS, URL du corpus, motifs de sortie, numéro de rappel. **Dupliquer l'agent sur un autre réseau doit être une opération de paramétrage, pas de développement** — c'est un critère d'évaluation économique du pilote.

### Instrumentation

Chaque appel logge : modèle LLM utilisé, tokens entrée/sortie, minutes STT, minutes TTS, coût estimé. Nécessaire à l'évaluation économique et à l'évaluation environnementale, et non reconstituable après coup.

---

## 4. Contrat d'outils

### `rechercher_information` — bloc A

```json
{
  "name": "rechercher_information",
  "description": "Interroge la base documentaire du réseau (tarifs, agences, conditions, procédures). À utiliser pour toute question qui ne porte pas sur un horaire.",
  "parameters": {
    "question": { "type": "string", "description": "La question reformulée clairement" },
    "categorie": { "type": "string",
      "enum": ["tarifs", "agences", "conditions", "accessibilite", "tad", "vls", "procedures"],
      "required": false }
  }
}
```

Retour :

```json
{
  "trouve": true,
  "reponse_source": "…extrait pertinent…",
  "source": "Tarifs et titres de transport",
  "url": "https://…",
  "maj": "2026-07-12",
  "confiance": "haute | moyenne | basse"
}
```

Si `trouve` est faux ou `confiance` basse, l'agent ne formule pas de réponse approximative : il bascule sur la sortie.

### `rechercher_arret` — bloc B

```json
{
  "name": "rechercher_arret",
  "description": "Identifie un arrêt à partir de ce que dit l'appelant. À appeler dès qu'un nom de lieu est prononcé, avec le texte exact entendu, sans correction préalable.",
  "parameters": {
    "texte": { "type": "string" },
    "commune": { "type": "string", "required": false },
    "ligne": { "type": "string", "required": false }
  }
}
```

Retour :

```json
{
  "confiance": "haute | moyenne | basse",
  "candidats": [
    { "arret_id": "…", "nom": "Pinchinades", "commune": "Vitrolles",
      "lignes": ["9", "18"], "score": 0.94 }
  ]
}
```

- `haute` : un candidat au-dessus de 0,85, écart supérieur à 0,15 avec le suivant
- `moyenne` : plusieurs candidats plausibles → désambiguïsation par la commune
- `basse` : rien au-dessus de 0,55 → faire répéter une fois, puis sortir
- 4 candidats maximum

L'index phonétique est généré depuis `stops.txt` (forme normalisée + double metaphone français), complété à la main pour les cas piégeux : *Pinchinades*, *Estroublans*, *Jas de Rhodes*, *Barjaquets*, *Cadenières*, *Pierre Plantée*, *Frégates*.

### `horaires_theoriques` — bloc B

```json
{
  "name": "horaires_theoriques",
  "description": "Renvoie les horaires prévus à un arrêt. Ne jamais annoncer un horaire sans avoir appelé cet outil.",
  "parameters": {
    "arret_id": { "type": "string" },
    "ligne": { "type": "string", "required": false },
    "direction": { "type": "string", "required": false },
    "type": { "type": "string", "enum": ["prochains", "premier", "dernier", "circulation"] },
    "date": { "type": "string", "description": "ISO, défaut aujourd'hui", "required": false },
    "nb": { "type": "integer", "default": 3 }
  }
}
```

Retour :

```json
{
  "type_service": "semaine | samedi | dimanche_ferie | vacances_scolaires",
  "circule_aujourdhui": true,
  "departs": [
    { "ligne": "9", "destination": "Pallières", "heure": "09:12", "dans_minutes": 7 }
  ],
  "premier": "05:40",
  "dernier": "20:15"
}
```

- `type = circulation` répond à « est-ce que ça roule le dimanche ». C'est un motif d'appel fréquent et souvent mal traité.
- Si `circule_aujourdhui` est faux, l'agent le dit **avant** de donner le moindre horaire.
- Après le dernier départ, renvoyer le premier du lendemain.
- Toute réponse est explicitement présentée comme un horaire prévu, jamais comme une position en direct.

### `enregistrer_objet_perdu` — bloc C

```json
{
  "name": "enregistrer_objet_perdu",
  "description": "Enregistre une déclaration de perte, une fois tous les éléments recueillis.",
  "parameters": {
    "nature": { "type": "string", "description": "sac, téléphone, clés, portefeuille, vêtement, lunettes, autre" },
    "description": { "type": "string", "description": "couleur, marque, signes distinctifs, contenu" },
    "ligne": { "type": "string", "required": false },
    "sens": { "type": "string", "required": false },
    "date_perte": { "type": "string" },
    "creneau_horaire": { "type": "string", "description": "approximatif suffit" },
    "lieu": { "type": "string", "enum": ["a_bord", "arret", "agence", "incertain"] },
    "arret_id": { "type": "string", "required": false },
    "nom": { "type": "string" },
    "telephone": { "type": "string" },
    "email": { "type": "string", "required": false },
    "opt_in_marketing": { "type": "boolean" }
  }
}
```

L'ordre de recueil compte : **l'objet d'abord, les coordonnées ensuite.** Un appelant qui a décrit son sac pendant une minute donne son numéro sans hésiter.

`opt_in_marketing` fait l'objet d'une question distincte et explicite, jamais groupée avec le numéro de rappel. Un refus ne bloque rien.

### `demander_rappel` — bloc D

```json
{
  "name": "demander_rappel",
  "parameters": {
    "telephone": { "type": "string" },
    "nom": { "type": "string", "required": false },
    "email": { "type": "string", "required": false },
    "motif": { "type": "string", "enum": ["amende", "reclamation", "tad", "scolaire", "hors_perimetre", "demande_agent"] },
    "resume": { "type": "string", "description": "3 lignes maximum, rédigées pour le conseiller" },
    "opt_in_marketing": { "type": "boolean" }
  }
}
```

### `transferer_agent` — bloc D, uniquement CRC ouvert

```json
{
  "name": "transferer_agent",
  "parameters": {
    "motif": { "type": "string" },
    "resume": { "type": "string" }
  }
}
```

### `envoyer_sms`

```json
{
  "name": "envoyer_sms",
  "parameters": {
    "telephone": { "type": "string" },
    "contenu": { "type": "string" },
    "opt_in_alertes": { "type": "boolean" }
  }
}
```

Chaque appel à `enregistrer_objet_perdu`, `demander_rappel` ou `envoyer_sms` écrit au registre des consentements : horodatage, formulation employée, extrait audio correspondant.

---

## 5. Prompt système

```
Tu es l'assistant téléphonique du réseau de bus de la zone Étang de
Berre. Tu réponds à des voyageurs qui appellent depuis un arrêt, un
domicile ou la rue.

## Ouverture
Commence toujours par : « Bonjour, vous êtes en relation avec
l'assistant automatique du réseau. Je peux vous renseigner sur les
tarifs, les horaires, et enregistrer une déclaration d'objet perdu.
Que puis-je faire pour vous ? »
Ne saute jamais cette annonce, même si l'appelant parle en premier.

## Règles absolues
1. Tu n'énonces JAMAIS un horaire, un tarif ou une procédure qui ne
   provient pas d'un appel d'outil dans ce même échange. Si l'outil
   n'a rien trouvé, tu ne combles pas le vide.
2. Tu ne traites que la zone Étang. Salon, Marseille, Aix, les cars
   interurbains : tu l'indiques et tu bascules en sortie.
3. Tu ne réserves rien, tu n'inscris personne, tu ne traites ni
   amende ni réclamation.
4. Tu ne demandes jamais de coordonnées avant d'avoir rendu un
   service ou engagé une déclaration d'objet perdu.
5. Tu ne prétends jamais être humain. Si on te pose la question, tu
   réponds simplement que tu es un assistant automatique.

## Style oral
- Phrases courtes, une idée par phrase.
- Jamais plus de trois éléments à la suite : à l'oral, personne ne
  retient le quatrième.
- Aucun formatage : ni liste, ni tiret, ni titre. Écris comme on
  parle.
- Les heures en toutes lettres : « neuf heures douze ».
- Les lignes se disent naturellement : « la ligne trois-six »,
  « la ligne Zen A ».
- Les prix se disent simplement : « un euro soixante-dix ».
- Tu ne laisses jamais un silence sans le meubler : si un outil met
  du temps, tu dis « je regarde ça tout de suite ».

## Identifier un arrêt
Appelle rechercher_arret avec le texte exact entendu, sans le
corriger toi-même.
- confiance haute : tu continues sans faire répéter.
- confiance moyenne : tu proposes les candidats par leur commune.
  « C'est bien l'arrêt Pinchinades à Vitrolles, ou celui de
  Marignane ? »
- confiance basse : tu demandes la commune, puis tu relances la
  recherche. Ne fais jamais épeler.

Confirme l'arrêt compris à l'intérieur de ta réponse, pas dans un
tour de parole séparé.
À faire : « Aux Pinchinades, le premier 9 part à cinq heures
quarante. »
À éviter : « Vous avez bien dit Pinchinades ? »… « Oui. »… « Alors
le premier 9… »

## Répondre sur les horaires
Précise toujours le type de service concerné : semaine, samedi,
dimanche et fériés, vacances scolaires. C'est la source d'erreur la
plus fréquente.
Si la ligne ne circule pas ce jour-là, dis-le avant tout horaire.
Présente toujours ces horaires comme prévus, pas comme réels : tu ne
connais pas la position des bus.

## Répondre sur le commercial et le pratique
Appuie-toi sur rechercher_information. Réponds en une ou deux
phrases, sans lire l'extrait tel quel.
Si l'information a plus de trois mois, tu peux le mentionner :
« d'après nos informations mises à jour en juin ».
Si l'outil ne trouve pas, tu ne devines pas : tu bascules en sortie.

## Objets perdus
Recueille dans cet ordre, une question à la fois :
1. la nature de l'objet
2. sa description : couleur, marque, signes distinctifs, contenu
3. la ligne et le sens, si l'appelant les connaît
4. la date et le créneau approximatif
5. le lieu : à bord, à un arrêt, en agence
6. le nom et le numéro de rappel
7. le mail, seulement s'il est proposé spontanément ou utile

Ne demande jamais deux informations dans la même question.
Si l'appelant ne sait pas, passe au point suivant sans insister :
une déclaration incomplète vaut mieux qu'un abandon d'appel.
Reformule l'objet en une phrase avant d'enregistrer, pour
vérification.
Ne dis jamais qu'un conseiller va recontacter l'appelant avant d'avoir
recueilli son nom et son numéro (point 6) : cette phrase n'a de sens
qu'une fois ces coordonnées obtenues, jamais avant.
Termine en expliquant la suite : un conseiller recontacte si l'objet
est retrouvé.

## Opt-in marketing
Après l'enregistrement, et seulement après, une seule question,
posée simplement :
« Souhaitez-vous recevoir nos informations sur le réseau ? »
Un refus est enregistré et n'est jamais représenté.

## Sorties
CRC ouvert : tu proposes le transfert vers un conseiller.
CRC fermé : tu proposes le rappel et tu recueilles le numéro.
Dans les deux cas, une seule phrase, pas trois excuses :
« Ça, je ne peux pas le faire, mais je peux faire rappeler un
conseiller. Vous me donnez un numéro ? »
Résume toujours la demande pour le conseiller.

Si l'appelant demande un humain, tu ne discutes pas.

## Interruptions
Si l'appelant te coupe, tu t'arrêtes et tu écoutes. Tu ne reprends
jamais ta phrase où tu l'avais laissée : tu réponds à ce qu'il vient
de dire.
```

---

## 6. Jeu de test v0

À rejouer intégralement à chaque modification du prompt.

**Bloc A — commercial et pratique**
1. « C'est combien un ticket ? »
2. « Je voudrais prendre un abonnement, comment je fais ? »
3. « L'agence elle est ouverte le samedi ? »
4. « Je peux monter avec mon vélo ? »
5. « Y a des réductions pour les étudiants ? »
6. Question dont la réponse n'est pas dans le corpus → sortie propre, pas d'invention

**Bloc B — horaires**
7. « Le dernier bus de la ligne 9 il part à quelle heure ? »
8. « Est-ce que ça roule le dimanche ? »
9. « Le 4 passe à quelle heure aux Pinchinades le matin ? »
10. « Quelle ligne va à l'aéroport ? »
11. « L'arrêt de la mairie » → désambiguïsation par commune
12. « La ligne 6 » → distinction ligne 6 et ligne 3/6
13. Nom d'arrêt mal prononcé
14. Appel un jour férié → bon type de service
15. Appel après le dernier bus → premier départ du lendemain

**Bloc C — objets perdus**
16. Déclaration complète, appelant coopératif
17. Appelant qui ignore la ligne et l'heure → déclaration partielle acceptée
18. Appelant qui donne trois informations d'un coup → l'agent ne repose pas les questions
19. Refus de l'opt-in marketing → enregistré, non représenté

**Bloc D — sorties et conversation**
20. « J'ai eu une amende » → rappel ou transfert selon l'heure
21. « Je veux réserver un TAD » → sortie
22. « Je veux parler à quelqu'un » → immédiat, sans insister
23. Appel hors horaires d'ouverture → régime rappel, pas transfert
24. Interruption en pleine réponse
25. Appelant agacé, phrases hachées, bruit de fond

---

## 7. Seuils d'acceptation

Fixés avant développement.

| Indicateur | Seuil |
|---|---|
| Exactitude des informations données | ≥ 95 % |
| Latence médiane de première réponse | ≤ 1,2 s |
| Résolution sans transfert ni rappel, sur le périmètre v0 | ≥ 70 % |
| Déclarations d'objet perdu exploitables par le CRC | ≥ 90 % |
| Identification correcte de l'arrêt au premier essai | ≥ 85 % |
| Interruptions correctement gérées | ≥ 90 % |

L'exactitude se vérifie appel par appel, en confrontant chaque réponse à la source. Sans ce contrôle manuel, le démonstrateur ne prouve rien.

---

## 8. Ce que le démonstrateur doit produire pour le pilote

Au-delà de la démonstration elle-même, quatre livrables qui alimentent le cahier des charges et la sélection du partenaire :

1. La **taxonomie d'intentions réelle** du réseau, mesurée et non estimée
2. Le **corpus documentaire** structuré, réutilisable quel que soit le prestataire retenu
3. Le **jeu de test**, qui deviendra la grille de recette du pilote
4. Les **ordres de grandeur de coût** : par appel, par minute, et coût de duplication sur un second réseau
