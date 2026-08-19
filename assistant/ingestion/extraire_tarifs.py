"""
Extrait la grille tarifaire complète du site du réseau vers
data/corpus/tarifs.md.

Cas particulier par rapport aux autres pages du corpus : le contenu
dépend de deux critères (Profil, Fréquence) choisis via un formulaire.
"Profile=All" combiné aux deux valeurs de Frequency donne la grille
complète en 2 requêtes HTTP simples — aucun rendu JavaScript
nécessaire (vérifié : le tableau de résultats est déjà dans le HTML
brut, prix inclus dans une colonne prévue pour l'impression).

Usage : python3 -m assistant.ingestion.extraire_tarifs
"""

import html as htmllib
import re
from datetime import date
from pathlib import Path
from urllib.request import urlopen

URL_BASE = "https://www.salonetangcotebleue.fr/fr/les-tarifs/7/Fare"
FREQUENCES = {"THM_FARE_2": "Occasionnellement", "THM_FARE_3": "Régulièrement"}
CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "corpus"

MOTIF_LIGNE = re.compile(
    r"<tr>\s*<td>\s*(?P<titre>.*?)\s*</td>\s*"
    r"<td[^>]*>(?P<pour_qui>.*?)</td>\s*"
    r"<td[^>]*>(?P<prix>.*?)</td>\s*"
    r"<td[^>]*>.*?</td>\s*</tr>",
    re.DOTALL,
)


def _nettoyer(fragment_html):
    texte = re.sub(r"<[^>]+>", " ", fragment_html)
    texte = htmllib.unescape(texte)
    return re.sub(r"\s+", " ", texte).strip()


# Noms officiels du site vs noms que les appelants utilisent réellement
# au téléphone. Constaté à l'évaluation Étape 4c : "carnet de tickets"
# ne matche rien dans le corpus, qui ne parle que de "TITRE 10 VOYAGES" ;
# pareil pour "abonnement" vs "PASS". Le prix et les conditions restent
# ceux du site, seul le nom usuel est ajouté à côté du nom officiel.
SYNONYMES = [
    (re.compile(r"TITRE 10 VOYAGES", re.IGNORECASE), "carnet de tickets, carnet de 10 voyages"),
    (re.compile(r"PASS (MENSUEL|ANNUEL)", re.IGNORECASE), "abonnement"),
    (re.compile(r"TICKET UNIT[ÉE]", re.IGNORECASE), "titre unitaire, ticket à l'unité, trajet simple, un seul trajet, un aller simple"),
]


def _synonyme(titre):
    for motif, nom_usuel in SYNONYMES:
        if motif.search(titre):
            return nom_usuel
    return None


def extraire_grille():
    lignes = []
    for code_frequence, nom_frequence in FREQUENCES.items():
        url = f"{URL_BASE}?Profile=All&Frequency={code_frequence}"
        with urlopen(url, timeout=30) as reponse:
            contenu = reponse.read().decode("utf-8")
        for m in MOTIF_LIGNE.finditer(contenu):
            lignes.append({
                "frequence": nom_frequence,
                "titre": _nettoyer(m.group("titre")),
                "pour_qui": _nettoyer(m.group("pour_qui")),
                "prix": _nettoyer(m.group("prix")),
            })
    return lignes


def ecrire_corpus(lignes):
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    md = [
        "# Les tarifs",
        "",
        f"Source : {URL_BASE}",
        "Catégorie : tarifs",
        f"Date d'extraction : {date.today().isoformat()}",
        "",
    ]
    # Un "## " par tarif individuel, pas un seul gros tableau par
    # fréquence : sinon une question sur UN tarif précis ("un carnet")
    # se noie dans un bloc qui en mélange 16 à la fois (constaté lors
    # de la vérification en conditions réelles de l'Étape 4b).
    for l in lignes:
        md.append(f"## {l['titre']} ({l['frequence']})")
        md.append("")
        nom_usuel = _synonyme(l["titre"])
        if nom_usuel:
            md.append(f"Couramment appelé : {nom_usuel}")
        md.append(f"Pour qui : {l['pour_qui']}")
        md.append(f"Prix : {l['prix']}")
        md.append("")

    chemin = CORPUS_DIR / "tarifs.md"
    chemin.write_text("\n".join(md), encoding="utf-8")
    print(f"{len(lignes)} tarifs écrits dans {chemin}", flush=True)


if __name__ == "__main__":
    ecrire_corpus(extraire_grille())
