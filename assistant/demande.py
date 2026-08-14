"""
Vérification manuelle rapide de la recherche documentaire : affiche les
blocs les plus proches d'une question, avec leur score et leur source.

Utile pour rejouer à la main un cas trouvé en échec par
assistant.evalcorpus et voir ce que le moteur a réellement remonté.

Usage : python3 -m assistant.demande "c'est combien un carnet"
        (uv run python -m assistant.demande "c'est combien un carnet")
"""

import sys

from assistant.outils.rechercher_information import chercher_blocs, rechercher_information

NB_RESULTATS = 5


def main():
    if len(sys.argv) < 2:
        print("Usage : python -m assistant.demande \"<question>\"")
        sys.exit(1)

    question = " ".join(sys.argv[1:])

    print(f"Question : {question!r}\n")

    reponse = rechercher_information(question)
    print("Ce que renvoie rechercher_information (utilisé par l'agent) :")
    if reponse["trouve"]:
        print(f"  confiance : {reponse['confiance']}")
        print(f"  source    : {reponse['source']}")
        print(f"  url       : {reponse['url']}")
        print(f"  maj       : {reponse['maj']}")
        print(f"  extrait   : {reponse['reponse_source'][:200]}...")
    else:
        print("  trouve : False -> l'agent bascule sur la sortie, ne répond rien.")

    print(f"\nTop {NB_RESULTATS} blocs (pour comprendre le classement) :")
    for score, bloc in chercher_blocs(question, n=NB_RESULTATS):
        print(f"  {score:.3f}  [{bloc['fichier']}] {bloc['source']}")


if __name__ == "__main__":
    main()
