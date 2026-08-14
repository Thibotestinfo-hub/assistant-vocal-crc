"""
Outil `rechercher_information` — bloc A. Contrat : spec §4.

Charge l'index (data/corpus_index.json, construit par
assistant.ingestion.indexer_corpus) une seule fois en mémoire, puis
compare l'embedding de la question à celui de chaque bloc par
similarité cosinus. Aucun appel de modèle de langage ici : c'est
l'agent vocal qui formule la réponse à partir de l'extrait renvoyé.

Seuils de confiance provisoires (voir Étape 4c) : à ajuster une fois
qu'on aura de vraies questions et leurs bonnes réponses attendues.
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


def rechercher_information(question, categorie=None):
    index, vecteurs = _charger_index()

    if categorie:
        indices_retenus = [i for i, b in enumerate(index) if b["categorie"] == categorie]
        if not indices_retenus:
            return {"trouve": False}
        index_filtre = [index[i] for i in indices_retenus]
        vecteurs_filtres = vecteurs[indices_retenus]
    else:
        index_filtre, vecteurs_filtres = index, vecteurs

    modele = _charger_modele()
    v_question = np.array(list(modele.embed([question]))[0])

    scores = vecteurs_filtres @ v_question / (
        np.linalg.norm(vecteurs_filtres, axis=1) * np.linalg.norm(v_question)
    )
    meilleur = int(np.argmax(scores))
    meilleur_score = float(scores[meilleur])

    if meilleur_score < SEUIL_BASSE:
        return {"trouve": False}

    bloc = index_filtre[meilleur]
    return {
        "trouve": True,
        "reponse_source": bloc["texte"],
        "source": bloc["source"],
        "url": bloc["url"],
        "maj": bloc["maj"],
        "confiance": "haute" if meilleur_score >= SEUIL_HAUTE else "moyenne",
    }
