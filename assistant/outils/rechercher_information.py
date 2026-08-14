"""
Outil `rechercher_information` — bloc A. Contrat : spec §4.

Charge l'index (data/corpus_index.json, construit par
assistant.ingestion.indexer_corpus) une seule fois en mémoire, puis
compare l'embedding de la question à celui de chaque bloc par
similarité cosinus. Aucun appel de modèle de langage ici : c'est
l'agent vocal qui formule la réponse à partir de l'extrait renvoyé.

Seuils de confiance provisoires (Étape 4b) : à recalibrer avec de
vraies mesures (Étape 4c, assistant.evalcorpus).
"""

import json
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding

INDEX_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "corpus_index.json"
MODELE = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

SEUIL_BASSE = 0.25
SEUIL_HAUTE = 0.45

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
        _modele = TextEmbedding(MODELE)
    return _modele


def chercher_blocs(question, categorie=None, n=5):
    """Renvoie les n blocs les plus proches de la question, triés du
    meilleur au moins bon, sous la forme [(score, bloc), ...].

    Réutilisé par l'outil rechercher_information (qui ne garde que le
    meilleur) et par assistant.evalcorpus (qui regarde les 5 premiers,
    comme le prévoit la méthode)."""
    index, vecteurs = _charger_index()

    if categorie:
        indices_retenus = [i for i, b in enumerate(index) if b["categorie"] == categorie]
        if not indices_retenus:
            return []
        index_filtre = [index[i] for i in indices_retenus]
        vecteurs_filtres = vecteurs[indices_retenus]
    else:
        index_filtre, vecteurs_filtres = index, vecteurs

    modele = _charger_modele()
    v_question = np.array(list(modele.embed([question]))[0])

    scores = vecteurs_filtres @ v_question / (
        np.linalg.norm(vecteurs_filtres, axis=1) * np.linalg.norm(v_question)
    )
    ordre = np.argsort(scores)[::-1][:n]
    return [(float(scores[i]), index_filtre[i]) for i in ordre]


def rechercher_information(question, categorie=None):
    resultats = chercher_blocs(question, categorie, n=1)
    if not resultats or resultats[0][0] < SEUIL_BASSE:
        return {"trouve": False}

    meilleur_score, bloc = resultats[0]
    return {
        "trouve": True,
        "reponse_source": bloc["texte"],
        "source": bloc["source"],
        "url": bloc["url"],
        "maj": bloc["maj"],
        "confiance": "haute" if meilleur_score >= SEUIL_HAUTE else "moyenne",
    }
