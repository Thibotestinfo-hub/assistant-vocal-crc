"""
Outil `rechercher_information` — bloc A. Contrat : spec §4.

Charge l'index (data/corpus_index.json, construit par
assistant.ingestion.indexer_corpus) une seule fois en mémoire, puis
combine deux signaux pour trouver le bon bloc :

- un score sémantique (similarité cosinus des embeddings), qui
  présélectionne les blocs dont le SENS se rapproche de la question ;
- un score lexical (mots significatifs de la question retrouvés tels
  quels dans le bloc), qui départage ce lot.

Le mélange des deux n'est pas un raffinement optionnel : mesuré à
l'évaluation Étape 4c (avec intfloat/multilingual-e5-large), le score
sémantique brut s'est révélé inexploitable seul sur ce corpus étroit —
la fourchette de score des mauvaises réponses était entièrement
contenue dans celle des bonnes. Le score lexical, lui, sépare nettement
les questions pièges (aucun mot en commun avec le corpus) des vraies
questions : c'est lui qui porte la décision "je ne sais pas".

Modèle actuel (paraphrase-multilingual-MiniLM-L12-v2) : repli temporaire
depuis e5-large, qui donnait un meilleur rappel mais dont le poids
(2,25 Go) a fait échouer le déploiement Clever Cloud (mémoire, quota
CPU, puis disque). Les seuils ci-dessous n'ont pas été remesurés avec
ce modèle : à revérifier via assistant.evalcorpus avant de faire
confiance aux chiffres de l'Étape 4c.

Aucun appel de modèle de langage ici : c'est l'agent vocal qui formule
la réponse à partir de l'extrait renvoyé.
"""

import json
import re
import unicodedata
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding

RACINE = Path(__file__).resolve().parent.parent.parent
INDEX_PATH = RACINE / "data" / "corpus_index.json"
MODELE = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Cache du modèle d'embeddings dans data/etat/ (le seul dossier qui
# survit aux redéploiements Clever Cloud, voir assistant/outils/db.py) :
# sans ça, fastembed retélécharge le modèle depuis Hugging Face à chaque
# redémarrage de l'application (cache par défaut dans un dossier non
# persistant), ce qui peut dépasser le délai d'attente de Clever Cloud
# et faire échouer le tout premier appel après chaque déploiement (502,
# constaté en production le 02/09/2026).
CACHE_MODELE = RACINE / "data" / "etat" / "modeles"

# Repli temporaire depuis e5-large (voir indexer_corpus.py) : ce modèle
# n'est pas un modèle de recherche asymétrique, pas de préfixe "query: ".
PREFIXE_QUESTION = ""

# Nombre de candidats retenus par la présélection sémantique, avant
# l'affinage lexical.
TAILLE_PRESELECTION = 10

MOTS_VIDES = {
    "le", "la", "les", "de", "des", "du", "un", "une", "est", "ce", "cet", "cette",
    "que", "qui", "quoi", "dans", "pour", "avec", "sur", "sous", "mon", "ma", "mes",
    "ton", "ta", "tes", "son", "sa", "ses", "vos", "votre", "notre", "nos", "leur",
    "leurs", "je", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles", "être",
    "avoir", "fait", "faire", "comment", "quel", "quelle", "quels", "quelles", "peux",
    "peut", "puis", "voudrais", "aussi", "bien", "tres", "plus", "moins", "tout",
    "tous", "toute", "toutes", "sont", "etre", "suis", "es", "sommes", "etes", "au",
    "aux", "en", "et", "ou", "donc", "car", "chez", "vers", "apres", "avant", "entre",
}

# Seuils provisoires sur le score combiné (Étape 4c) : à recalibrer une
# fois les deux signaux mesurés ensemble avec de vraies questions.
SEUIL_BASSE = 0.3
SEUIL_HAUTE = 0.6

# Nombre minimum de mots significatifs partagés pour accepter un candidat
# (voir rechercher_information). Passé à 2 le 04/09 pour départager un
# document correct d'un document seulement voisin par le sujet, mais
# revenu à 1 le jour même : sur une question courte à 2 mots significatifs
# dont un mot interrogatif ("C'est combien un ticket ?" -> "combien",
# "ticket"), "combien" ne peut structurellement jamais apparaître dans un
# texte de réponse — exiger 2 mots revenait à rejeter systématiquement ce
# genre de question. Mesuré : 69% de bonnes réponses au lieu de 80% avec
# ce réglage. Le problème des faux positifs en position 1 (voir
# rechercher_information) reste entier, à traiter autrement.
SEUIL_MOTS_MINIMUM = 1

_index = None
_vecteurs = None
_modele = None


def _charger_index():
    global _index, _vecteurs
    if _index is None:
        _index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        _vecteurs = np.array([b["vecteur"] for b in _index])
    return _index, _vecteurs


def _charger_modele():
    global _modele
    if _modele is None:
        # En local, data/etat/ n'existe pas forcément encore (sur Clever
        # Cloud, c'est le point de montage du FS Bucket, déjà présent).
        CACHE_MODELE.mkdir(parents=True, exist_ok=True)
        _modele = TextEmbedding(MODELE, cache_dir=str(CACHE_MODELE))
    return _modele


def _normaliser(texte):
    forme = unicodedata.normalize("NFD", texte)
    return "".join(c for c in forme if unicodedata.category(c) != "Mn").lower()


LONGUEUR_RADICAL = 6


def _mots_significatifs(question):
    """Mots courts mais numériques (âge, prix, poids...) gardés malgré
    tout : "50 euros" ou "20 kg" est justement le genre de détail précis
    qui distingue une vraie question d'une question piège."""
    mots = re.findall(r"[a-z0-9]+", _normaliser(question))
    return [m for m in mots if (m.isdigit() or len(m) >= 4) and m not in MOTS_VIDES]


def _radical(mot):
    """Les 6 premiers caractères d'un mot, pour absorber pluriels et
    variations de genre sans vrai stemmer ("étudiant"/"étudiants",
    "réduction"/"réductions") : comparer les mots entiers en substring
    ratait ces accords simples (constaté à l'évaluation Étape 4c)."""
    return mot[:LONGUEUR_RADICAL]


def _mots_trouves(mots_question, bloc):
    """Nombre de mots significatifs de la question dont le radical se
    retrouve dans le titre et le texte du bloc (compte brut, utilisé par
    _score_lexical et par le veto à seuil minimum de rechercher_information)."""
    if not mots_question:
        return 0
    texte_normalise = _normaliser(f"{bloc['source']} {bloc['texte']}")
    return sum(1 for m in mots_question if _radical(m) in texte_normalise)


def _score_lexical(mots_question, bloc):
    """Part des mots significatifs de la question dont le radical se
    retrouve dans le titre et le texte du bloc."""
    if not mots_question:
        return 0.0
    return _mots_trouves(mots_question, bloc) / len(mots_question)


def chercher_blocs(question, categorie=None, n=5, categories_actives=None):
    """Renvoie les n blocs les plus proches de la question, triés du
    meilleur au moins bon, sous la forme [(score_combine, bloc), ...].

    categories_actives : si fourni (voir assistant.backoffice.activation,
    categories_actives()), les blocs dont la categorie n'y figure pas sont
    exclus des candidats — même quand `categorie` n'est pas précisé par
    l'appelant, pour qu'un sujet coupé depuis le back-office ne puisse
    jamais ressortir par une question formulée vaguement. None (par
    défaut) : pas de filtrage, utilisé par assistant.evalcorpus qui doit
    évaluer tout le corpus indépendamment de l'activation en cours.

    Réutilisé par l'outil rechercher_information (qui ne garde que le
    meilleur) et par assistant.evalcorpus (qui regarde les 5 premiers,
    comme le prévoit la méthode)."""
    index, vecteurs = _charger_index()

    indices_retenus = [
        i for i, b in enumerate(index)
        if (categorie is None or b["categorie"] == categorie)
        and (categories_actives is None or b["categorie"] in categories_actives)
    ]
    if categorie or categories_actives is not None:
        if not indices_retenus:
            return []
        index_filtre = [index[i] for i in indices_retenus]
        vecteurs_filtres = vecteurs[indices_retenus]
    else:
        index_filtre, vecteurs_filtres = index, vecteurs

    modele = _charger_modele()
    v_question = np.array(list(modele.embed([PREFIXE_QUESTION + question]))[0])

    scores_semantiques = vecteurs_filtres @ v_question / (
        np.linalg.norm(vecteurs_filtres, axis=1) * np.linalg.norm(v_question)
    )
    ordre_semantique = np.argsort(scores_semantiques)[::-1][:TAILLE_PRESELECTION]

    mots_question = _mots_significatifs(question)
    candidats = [(float(scores_semantiques[i]), index_filtre[i]) for i in ordre_semantique]

    # Le score sémantique ne varie que sur une fourchette étroite dans ce
    # lot (voir docstring du module) : on le ramène à une échelle 0-1
    # relative au lot pour pouvoir le mélanger avec le score lexical.
    scores_sem = [c[0] for c in candidats]
    mini, maxi = min(scores_sem), max(scores_sem)
    etendue = maxi - mini or 1.0

    resultats = []
    for score_sem, bloc in candidats:
        score_sem_relatif = (score_sem - mini) / etendue
        score_lex = _score_lexical(mots_question, bloc)
        combine = 0.5 * score_sem_relatif + 0.5 * score_lex
        resultats.append((combine, bloc))

    resultats.sort(key=lambda r: r[0], reverse=True)
    return resultats[:n]


def rechercher_information(question, categorie=None, categories_actives=None):
    """N'examinait auparavant que le tout premier candidat (n=1) : si
    celui-ci ne partageait aucun mot avec la question (véto lexical), on
    répondait trouve=False même quand un candidat suivant, tout aussi
    bien classé, aurait parfaitement répondu — mesuré à l'évaluation du
    03/09/2026 (rappel top-5 100%, réponse outil seulement 80%, l'écart
    venait presque entièrement de ce cas). On regarde maintenant les 5
    meilleurs candidats dans l'ordre et on renvoie le premier qui passe
    les deux vérifications, plutôt que d'abandonner au premier échec.

    Ajustement du 04/09/2026, mesuré sur le même jeu d'évaluation : le
    score sémantique combiné ne fait plus abandonner la recherche (voir
    le continue plus bas) — le bon document peut être en 3e position avec
    un score déjà sous SEUIL_BASSE, sans être moins pertinent pour autant.

    Piste testée le même jour et abandonnée : exiger plusieurs mots
    partagés (pas un seul) pour durcir le véto lexical. Casse trop de
    questions courtes dont un des rares mots significatifs est un mot
    interrogatif qui ne peut jamais apparaître dans un texte de réponse
    ("combien" dans "c'est combien un ticket ?") — mesuré à 69% au lieu de
    80%. Le problème que ça visait (un premier candidat FAUX qui passe le
    véto avec un seul mot en commun, générique) reste entier, à traiter
    autrement — voir docs/prochaines-etapes.md."""
    resultats = chercher_blocs(question, categorie, n=5, categories_actives=categories_actives)
    mots_question = _mots_significatifs(question)

    for score, bloc in resultats:
        if score < SEUIL_BASSE:
            # Pas de break ici : contrairement à un premier réflexe, un
            # candidat plus bas dans le score sémantique combiné n'est pas
            # forcément moins pertinent — mesuré le 04/09 sur "abonnement",
            # où le bon document tombait sous SEUIL_BASSE en 3e position et
            # n'était donc jamais atteint. C'est le test lexical juste
            # dessous, pas ce seuil, qui porte la décision "je ne sais pas"
            # (voir docstring du module).
            continue
        # Aucun mot de la question ne se retrouve dans ce candidat : quel
        # que soit son score sémantique, ce n'est pas une réponse fiable
        # (c'est ce signal, pas le score sémantique, qui distingue le
        # mieux les questions pièges — voir docstring du module) — on
        # regarde le candidat suivant plutôt que d'abandonner.
        if mots_question and _mots_trouves(mots_question, bloc) < min(SEUIL_MOTS_MINIMUM, len(mots_question)):
            continue
        return {
            "trouve": True,
            "reponse_source": bloc["texte"],
            "source": bloc["source"],
            "url": bloc["url"],
            "maj": bloc["maj"],
            "confiance": "haute" if score >= SEUIL_HAUTE else "moyenne",
        }
    return {"trouve": False}
