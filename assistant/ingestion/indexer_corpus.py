"""
Découpe les pages de data/corpus/ en blocs de 400 à 800 mots et calcule
leur vecteur d'embedding, pour que assistant.outils.rechercher_information
puisse comparer une question à chaque bloc.

Stockage choisi : un simple fichier JSON (data/corpus_index.json), chargé
en mémoire au démarrage de l'API. Pas de base vectorielle : on parle de
quelques dizaines de blocs, pas de millions (voir CLAUDE.md).

Usage : python3 -m assistant.ingestion.indexer_corpus
"""

import json
import re
from pathlib import Path

from fastembed import TextEmbedding

CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "corpus"
INDEX_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "corpus_index.json"

MODELE = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MOTS_MIN_BLOC = 400
MOTS_MAX_BLOC = 800


def _lire_entete(texte):
    """Récupère titre/source/catégorie/date en tête de fichier, et
    renvoie (metadonnees, reste_du_texte)."""
    lignes = texte.split("\n")
    titre = lignes[0].lstrip("# ").strip()
    meta = {"titre": titre, "url": "", "categorie": "", "maj": ""}
    i = 1
    while i < len(lignes) and lignes[i].strip() == "":
        i += 1
    while i < len(lignes) and ":" in lignes[i]:
        cle, _, valeur = lignes[i].partition(":")
        cle = cle.strip().lower()
        valeur = valeur.strip()
        if cle == "source":
            meta["url"] = valeur
        elif cle == "catégorie":
            meta["categorie"] = valeur
        elif cle == "date d'extraction":
            meta["maj"] = valeur
        i += 1
    return meta, "\n".join(lignes[i:]).strip()


def _decouper_en_sections(corps):
    """Coupe sur les titres de niveau 2 (## ...). S'il n'y en a aucun,
    tout le texte forme une seule section sans titre propre."""
    morceaux = re.split(r"^## (.+)$", corps, flags=re.MULTILINE)
    if len(morceaux) == 1:
        return [(None, corps.strip())]
    sections = []
    if morceaux[0].strip():
        sections.append((None, morceaux[0].strip()))
    for i in range(1, len(morceaux), 2):
        sections.append((morceaux[i].strip(), morceaux[i + 1].strip()))
    return sections


def _redecouper_si_trop_long(texte):
    """Une section de plus de MOTS_MAX_BLOC mots est reformée en blocs
    de MOTS_MIN_BLOC à MOTS_MAX_BLOC mots, sans couper un paragraphe
    en deux."""
    paragraphes = [p for p in texte.split("\n\n") if p.strip()]
    blocs, bloc_courant, mots_courant = [], [], 0

    for p in paragraphes:
        n = len(p.split())
        if mots_courant + n > MOTS_MAX_BLOC and mots_courant >= MOTS_MIN_BLOC:
            blocs.append("\n\n".join(bloc_courant))
            bloc_courant, mots_courant = [], 0
        bloc_courant.append(p)
        mots_courant += n

    if bloc_courant:
        blocs.append("\n\n".join(bloc_courant))
    return blocs


def decouper_fichier(chemin):
    meta, corps = _lire_entete(chemin.read_text(encoding="utf-8"))
    blocs = []
    for titre_section, texte_section in _decouper_en_sections(corps):
        if not texte_section:
            continue
        for morceau in _redecouper_si_trop_long(texte_section):
            if len(morceau.split()) < 5:  # bruit résiduel (ex. juste "---")
                continue
            titre_complet = meta["titre"] + (f" — {titre_section}" if titre_section else "")
            blocs.append({
                "fichier": chemin.name,
                "source": titre_complet,
                "url": meta["url"],
                "categorie": meta["categorie"],
                "maj": meta["maj"],
                "texte": morceau,
            })
    return blocs


def construire_index():
    tous_les_blocs = []
    for chemin in sorted(CORPUS_DIR.glob("*.md")):
        blocs = decouper_fichier(chemin)
        tous_les_blocs.extend(blocs)
        print(f"  {chemin.name} -> {len(blocs)} bloc(s)")

    print(f"\n{len(tous_les_blocs)} blocs au total. Calcul des embeddings ({MODELE})...")
    modele = TextEmbedding(MODELE)
    vecteurs = list(modele.embed([b["texte"] for b in tous_les_blocs]))
    for bloc, vecteur in zip(tous_les_blocs, vecteurs):
        bloc["vecteur"] = vecteur.tolist()

    INDEX_PATH.write_text(json.dumps(tous_les_blocs, ensure_ascii=False), encoding="utf-8")
    print(f"Index écrit dans {INDEX_PATH}")


if __name__ == "__main__":
    construire_index()
