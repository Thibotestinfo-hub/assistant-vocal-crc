# Checklist avant la démo du 09/09

## A. Scénarios d'appel à tester toi-même avant la démo

Objectif : vérifier que le parcours est fluide sur les cas qui vont
probablement sortir devant l'équipe — pas besoin de suivre l'ordre,
mais faire chaque ligne au moins une fois.

- [ ] Horaires simples : « Le prochain 9 passe à quelle heure aux
      Pinchinades ? » — si la reconnaissance bute, avoir en tête la
      piste "termes de domaine" ElevenLabs (voir suivi).
- [ ] Horaires sur un créneau : « Il y a un bus entre 8h et 8h30 ? »
- [ ] Tarifs — les deux formulations qui viennent d'être corrigées :
      « quel est le prix d'un billet ? » et « combien coûte un titre de
      transport ? »
- [ ] Tarifs — abonnement scolaire (déjà testé, sert de repère de
      qualité) : « comment abonner mon enfant au réseau ? »
- [ ] Objet perdu : déclarer un objet perdu de bout en bout.
- [ ] Vélo en libre service : une question simple sur LeVélo+.
- [ ] Transport à la demande : « comment réserver le bus à la
      demande ? »
- [ ] Amendes : « comment payer une amende ? » — cas corrigé le 04/09,
      à reconfirmer après le rafraîchissement du corpus.
- [ ] Une question hors périmètre volontaire (ex. horaires d'un autre
      réseau) : vérifier que l'assistant dit "je ne sais pas" plutôt
      que d'inventer, et propose le transfert.
- [ ] Une interruption volontaire pendant que l'assistant parle : couper
      la parole au milieu d'une phrase, vérifier qu'il s'arrête et
      écoute plutôt que de continuer par-dessus.
- [ ] Écouter la clôture d'appel : formule chaleureuse, "bonne journée"
      ou "bonne soirée" selon l'heure réelle de l'appel.
- [ ] Un appel après 17h30 si possible (ou vérifier via le curl
      ci-dessous) pour confirmer "bonne soirée".

## B. Vérification rapide sans décrocher le téléphone

```bash
# Confirme la formule de clôture selon l'heure actuelle
curl -sS -X POST https://app-69667b75-9864-49e3-ada5-810b7e279002.cleverapps.io/webhooks/elevenlabs/personnalisation \
  -H "Authorization: Bearer $(grep API_TOKEN .env | cut -d= -f2)" \
  -H "Content-Type: application/json" -d '{}'

# Confirme que les deux cas corrigés répondent bien
curl -sS -X POST https://app-69667b75-9864-49e3-ada5-810b7e279002.cleverapps.io/outils/rechercher_information \
  -H "Authorization: Bearer $(grep API_TOKEN .env | cut -d= -f2)" \
  -H "Content-Type: application/json" -d '{"question": "combien coute un titre de transport ?"}'

curl -sS -X POST https://app-69667b75-9864-49e3-ada5-810b7e279002.cleverapps.io/outils/rechercher_information \
  -H "Authorization: Bearer $(grep API_TOKEN .env | cut -d= -f2)" \
  -H "Content-Type: application/json" -d '{"question": "comment payer une amende ?"}'
```

## C. Parcours back-office à répéter (pour toi, et pour que les
collègues puissent se projeter)

- [ ] Onglet **Live** : montrer le bouton d'arrêt général, expliquer
      qu'il coupe tout le monde (pas un outil précis).
- [ ] Onglet **Live** : basculer un outil (ex. Vélo en libre service)
      et montrer que l'assistant en tient compte immédiatement sur un
      appel réel — bon moment pour illustrer la personnalisation du
      message d'accueil.
- [ ] Onglet **Suivi** : parcourir le tableau des appels, ouvrir le
      détail d'un appel (transcription), montrer l'export CSV objets
      perdus et demandes de rappel.
- [ ] Onglet **Suivi** : expliquer les indicateurs (durée moyenne,
      coût, satisfaction) — dire clairement ce qui est fiable
      aujourd'hui (le coût, la durée) et ce qui ne l'est pas encore
      (empreinte carbone, "pas encore de méthode fiable" — l'assumer
      plutôt que de le cacher, cohérent avec l'esprit "je ne sais pas
      plutôt qu'une approximation" du projet).
- [ ] Onglet **Prononciation** : montrer comment ajouter une règle,
      pour que les collègues comprennent qu'ils pourraient le faire
      eux-mêmes.

## D. À dire explicitement pendant la démo (gérer les attentes)

- C'est un POC en expérimentation active, pas un produit fini — les
  retours d'aujourd'hui nourrissent encore des corrections chaque
  semaine (ex. "billet"/"titre de transport" corrigé hier soir).
- Les noms d'arrêts inhabituels peuvent parfois être mal compris au
  téléphone (limite de la reconnaissance vocale, pas du moteur de
  recherche d'arrêt) — un problème connu, une piste d'amélioration
  identifiée (termes de domaine ElevenLabs), pas encore activée.
- Les données affichées dans "Suivi" sont celles de la phase de test
  (appels internes des derniers jours), pas de vrais appelants.

## E. Pense-bête technique (à faire par toi avant/pendant la démo)

- [ ] Ajouter les termes piégeux à la liste de boost ASR ElevenLabs si
      le réglage existe (Pinchinades, Estroublans, Jas de Rhodes,
      Barjaquets, Cadenières, Pierre Plantée, Frégates).
- [ ] Vérifier que `{{formule_cloture}}` est bien utilisé dans le
      prompt (remplace le texte fixe "bonne journée").
