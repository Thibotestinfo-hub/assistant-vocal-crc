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

# e5-large donnait un meilleur rappel sémantique seul (mesuré à l'Étape 4c),
# mais son poids (2,25 Go) a fait échouer le déploiement Clever Cloud
# (mémoire, puis quota CPU, puis disque) : repli sur ce modèle plus léger,
# déjà validé en production, en attendant une solution moins coûteuse.
# Pas de préfixe "passage: " ici : MiniLM n'est pas un modèle de recherche
# asymétrique, il n'en a pas besoin (voir rechercher_information.py).
PREFIXE_PASSAGE = ""

MOTIF_LIEN = re.compile(r"\[[^\]]*\]\([^)]*\)")


def _est_un_sommaire(texte):
    """Une page qui ne fait que lister des liens vers ses sous-pages (ex.
    accessibilite.md, conseils-pour-voyager.md) n'apporte aucune réponse :
    l'indexer risque de la faire gagner par son vocabulaire générique sans
    jamais donner d'information utile à l'appelant (constaté à l'évaluation
    Étape 4c). On retire les liens et on regarde ce qu'il reste.

    Il faut au moins 2 liens pour envisager "sommaire" : sinon des fiches
    courtes mais réelles (ex. les tarifs, juste "Pour qui" + "Prix", sans
    aucun lien) se faisaient exclure à tort — régression constatée en
    vérifiant le nombre de blocs de tarifs.md après ce filtre."""
    liens = MOTIF_LIEN.findall(texte)
    if len(liens) < 2:
        return False
    sans_liens = MOTIF_LIEN.sub("", texte)
    return len(sans_liens.split()) < 15


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
    """Coupe sur les titres de niveau 2 et 3 (## ou ### ...). S'il n'y en
    a aucun, tout le texte forme une seule section sans titre propre.

    Certaines pages du site (nous-contacter, tad...) n'utilisent que des
    ### en dessous de leur unique ## : s'arrêter au niveau 2 les laissait
    former un seul bloc géant qui mélangeait plusieurs sujets (constaté
    lors de l'évaluation Étape 4c : les horaires téléphoniques, noyés
    dans l'adresse postale, perdaient face à un autre bloc plus ciblé)."""
    morceaux = re.split(r"^#{2,3} (.+)$", corps, flags=re.MULTILINE)
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
            if _est_un_sommaire(morceau):
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
    # flush=True partout ici : sans ça, la sortie reste bufferisée tant
    # que le tampon ne se remplit pas, ce qui a déjà rendu un déploiement
    # Clever Cloud illisible dans les logs — impossible de distinguer un
    # calcul simplement lent d'un blocage réel (constaté à l'usage).
    tous_les_blocs = []
    for chemin in sorted(CORPUS_DIR.glob("*.md")):
        blocs = decouper_fichier(chemin)
        tous_les_blocs.extend(blocs)
        print(f"  {chemin.name} -> {len(blocs)} bloc(s)", flush=True)

    print(f"\n{len(tous_les_blocs)} blocs au total. Chargement du modèle ({MODELE})...", flush=True)
    modele = TextEmbedding(MODELE)
    print("Modèle chargé. Calcul des embeddings...", flush=True)
    # Le titre est inclus dans le texte comparé à la question (mais pas
    # dans bloc["texte"], qui reste la réponse propre renvoyée à l'appelant) :
    # un bloc court comme "Nous appeler" perd son seul repère thématique
    # sans lui, une fois isolé de son fichier.
    textes_a_vectoriser = [PREFIXE_PASSAGE + f"{b['source']}. {b['texte']}" for b in tous_les_blocs]
    # e5-large est un modèle lourd (560M paramètres) : le vectoriser en une
    # seule fournée de 81 textes a fait tuer le processus par manque de
    # mémoire lors de la vérification (Codespaces). De petits paquets
    # limitent le pic mémoire, au prix d'un peu de temps.
    for i, (bloc, vecteur) in enumerate(zip(tous_les_blocs, modele.embed(textes_a_vectoriser, batch_size=4))):
        bloc["vecteur"] = vecteur.tolist()
        if (i + 1) % 20 == 0 or i + 1 == len(tous_les_blocs):
            print(f"  {i + 1}/{len(tous_les_blocs)} blocs vectorisés", flush=True)

    INDEX_PATH.write_text(json.dumps(tous_les_blocs, ensure_ascii=False), encoding="utf-8")
    print(f"Index écrit dans {INDEX_PATH}", flush=True)


if __name__ == "__main__":
    construire_index()
