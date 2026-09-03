"""
Extrait les pages "discursives" du site du réseau vers data/corpus/ —
un fichier markdown par page, avec titre, URL et date d'extraction en
en-tête. Aucune rédaction manuelle : tout vient du site.

Volontairement absentes de la liste PAGES : les fiches horaires (elles
viennent du GTFS, pas du corpus — une fiche mal extraite produirait des
horaires faux), et les pages purement institutionnelles (mentions
légales, "qui sommes-nous", offres d'emploi...) qui ne répondent à
aucune question de voyageur.

Usage : python3 -m assistant.ingestion.extraire_corpus
"""

from datetime import date
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from markdownify import markdownify

BASE_URL = "https://www.salonetangcotebleue.fr"
CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "corpus"

# (chemin, nom de fichier, catégorie). Le nom de fichier est choisi à la
# main pour rester lisible ; le chemin vient du "Plan du site" du réseau.
# La catégorie reprend l'enum de rechercher_information dans la spec
# (tarifs, agences, conditions, accessibilite, tad, vls, procedures,
# amendes — cette dernière isolée de procedures le 03/09/2026, pour
# permettre de désactiver les amendes depuis le back-office sans couper
# la FAQ générale au passage, voir docs/prochaines-etapes.md).
PAGES = [
    ("/fr/aide-et-accessibilite/54", "accessibilite", "accessibilite"),
    ("/fr/faq/12", "faq", "procedures"),
    ("/fr/transports-a-la-demande-tad/1035", "tad", "tad"),
    ("/fr/proces-verbaux-pv-/1034", "amendes", "amendes"),
    ("/fr/nos-boutiques/74", "boutiques", "agences"),
    ("/fr/depositaires-agrees/1036", "depositaires-agrees", "agences"),
    ("/fr/nos-dat-distributeurs/1041", "distributeurs", "agences"),
    ("/fr/levelo/83", "velo", "vls"),
    ("/fr/conditions-generales-dutilisation/186", "conditions-generales", "conditions"),
    ("/fr/conseils-pour-voyager/1021", "conseils-pour-voyager", "conditions"),
    ("/fr/pass-integral-metropolitain/1004", "pass-integral-metropolitain", "tarifs"),
    ("/fr/paiment-sans-contact/1011", "paiement-sans-contact", "tarifs"),
    ("/fr/transport-de-groupes/1042", "transport-de-groupes", "conditions"),
    ("/fr/prime-transport/72", "prime-transport", "tarifs"),
    ("/fr/nous-contacter/94", "nous-contacter", "agences"),
    ("/fr/transports-scolaires/1024", "transports-scolaires", "conditions"),
    ("/fr/voyager-dans-la-metropole/1027", "voyager-dans-la-metropole", "conditions"),
    ("/fr/la-mobilite-pour-les-particuliers-et-les-entrepris/1014", "mobilite-particuliers-entreprises", "conditions"),
]

# Sélecteurs CSS des blocs qui ne sont jamais du contenu utile sur ce
# site (fil d'Ariane, partage, formulaires/menus déroulants de fichiers,
# scripts). Repéré en comparant plusieurs pages : sans ce nettoyage, une
# page comme "Nous contacter" traîne un menu déroulant de 8000
# caractères de noms de fichiers, sans rapport avec son contenu réel.
SELECTEURS_BRUIT = [
    "nav[aria-label]", ".tool-links", ".services-list", ".message-container",
    "script", "style", "noscript", "form",
]


def _telecharger(chemin):
    requete = Request(BASE_URL + chemin, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(requete, timeout=30) as reponse:
        return reponse.read().decode("utf-8", errors="replace")


def extraire_page(chemin):
    html = _telecharger(chemin)
    soup = BeautifulSoup(html, "html.parser")

    titre_tag = soup.select_one("h1")
    titre = titre_tag.get_text(strip=True) if titre_tag else chemin

    main = soup.select_one("main")
    if main is None:
        return None

    for selecteur in SELECTEURS_BRUIT:
        for element in main.select(selecteur):
            element.decompose()

    # Le titre h1 de la page est déjà repris dans notre propre en-tête
    # (juste en dessous) : on l'enlève ici pour ne pas le dupliquer.
    h1_dans_main = main.select_one("h1")
    if h1_dans_main is not None:
        h1_dans_main.decompose()

    contenu_md = markdownify(str(main), heading_style="ATX").strip()
    # Markdownify laisse souvent 3+ lignes vides d'affilée après avoir
    # retiré des blocs : on les ramène à une seule ligne vide.
    while "\n\n\n" in contenu_md:
        contenu_md = contenu_md.replace("\n\n\n", "\n\n")

    return titre, contenu_md


def ecrire_page(chemin, nom_fichier, categorie):
    """Renvoie True si la page a été écrite, False si elle est
    inaccessible ou sans contenu principal — ne lève jamais d'exception :
    une page en échec ne doit pas empêcher les autres d'être traitées
    (utile notamment pour assistant.corpus --refresh, qui a besoin de
    voir toutes les pages en échec d'un coup, pas seulement la première)."""
    try:
        resultat = extraire_page(chemin)
    except URLError as exc:
        print(f"  ⚠️  {chemin} : inaccessible ({exc.reason}), fichier existant conservé tel quel", flush=True)
        return False

    if resultat is None:
        print(f"  ⚠️  {chemin} : pas de contenu principal trouvé, ignoré", flush=True)
        return False

    titre, contenu_md = resultat
    entete = (
        f"# {titre}\n\n"
        f"Source : {BASE_URL}{chemin}\n"
        f"Catégorie : {categorie}\n"
        f"Date d'extraction : {date.today().isoformat()}\n\n"
    )
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    (CORPUS_DIR / f"{nom_fichier}.md").write_text(entete + contenu_md, encoding="utf-8")
    print(f"  {nom_fichier}.md ({len(contenu_md)} caractères) <- {chemin}", flush=True)
    return True


def extraire_corpus():
    """Renvoie la liste des (chemin, nom_fichier) en échec — pages
    inaccessibles ou sans contenu — pour qu'un appelant (assistant.corpus
    --refresh) puisse les signaler sans avoir à reparser la sortie
    texte."""
    en_echec = []
    for chemin, nom_fichier, categorie in PAGES:
        if not ecrire_page(chemin, nom_fichier, categorie):
            en_echec.append((chemin, nom_fichier))
    reussies = len(PAGES) - len(en_echec)
    print(f"\n{reussies}/{len(PAGES)} pages extraites dans {CORPUS_DIR}", flush=True)
    return en_echec


if __name__ == "__main__":
    extraire_corpus()
