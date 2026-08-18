"""
Rafraîchissement du corpus documentaire — Étape 4d de la méthode.

Relance l'extraction (tarifs + pages) et rapporte ce qui a changé
depuis le dernier passage : pages modifiées, pages nouvelles dans
data/corpus/, pages devenues inaccessibles (probablement disparues ou
déplacées sur le site — l'ancien fichier est alors conservé tel quel,
jamais supprimé, pour ne perdre aucune donnée déjà extraite).

Limite connue, assumée : cette commande ne peut signaler des
changements que sur les pages déjà listées dans
assistant.ingestion.extraire_corpus.PAGES. Elle ne découvre pas de
nouvelles pages publiées sur le site — ça demanderait un parcours du
plan du site (sitemap.xml), jamais construit (voir
docs/methode-developpement.md, Étape 4a). Ajouter une page nouvelle
reste une action manuelle : l'ajouter à PAGES.

Usage : python3 -m assistant.corpus --refresh
        (à lancer chaque semaine, et à chaque enrichissement du site)
"""

import sys
from urllib.error import URLError

from assistant.ingestion.extraire_corpus import CORPUS_DIR, extraire_corpus
from assistant.ingestion.extraire_tarifs import ecrire_corpus, extraire_grille


def _instantane():
    if not CORPUS_DIR.exists():
        return {}
    return {p.name: p.read_text(encoding="utf-8") for p in CORPUS_DIR.glob("*.md")}


def rafraichir():
    avant = _instantane()

    print("Extraction des tarifs...")
    try:
        ecrire_corpus(extraire_grille())
    except URLError as exc:
        print(f"  ⚠️  grille tarifaire inaccessible ({exc.reason}), tarifs.md existant conservé tel quel")

    print("\nExtraction des autres pages...")
    en_echec = extraire_corpus()

    apres = _instantane()

    modifiees = sorted(f for f in avant if f in apres and avant[f] != apres[f])
    nouvelles = sorted(f for f in apres if f not in avant)

    print("\n--- Rapport de rafraîchissement ---")

    print(f"\nModifiées ({len(modifiees)}) :")
    for f in modifiees:
        print(f"  ~ {f}")

    print(f"\nNouvelles dans data/corpus/ ({len(nouvelles)}) :")
    for f in nouvelles:
        print(f"  + {f}")

    print(f"\nInaccessibles cette fois, probablement disparues ou déplacées ({len(en_echec)}) :")
    for chemin, nom_fichier in en_echec:
        print(f"  ! {nom_fichier}.md <- {chemin}  (fichier existant conservé, à vérifier à la main)")

    print(
        "\nRappel : cette commande ne détecte que des changements sur les pages déjà "
        "connues (assistant.ingestion.extraire_corpus.PAGES). Elle ne découvre pas de "
        "nouvelles pages publiées sur le site — à vérifier de temps en temps à la main."
    )

    if modifiees or en_echec:
        print(
            "\nDu contenu a changé : pensez à relancer "
            "`python -m assistant.ingestion.indexer_corpus` puis "
            "`python -m assistant.evalcorpus` pour vérifier que la recherche "
            "documentaire n'a pas régressé."
        )

    return {"modifiees": modifiees, "nouvelles": nouvelles, "en_echec": en_echec}


def main():
    if "--refresh" not in sys.argv:
        print("Usage : python -m assistant.corpus --refresh")
        sys.exit(1)
    rafraichir()


if __name__ == "__main__":
    main()
