"""
Le CRC (Salon-de-Provence) est ouvert ou fermé selon un calendrier réel
(data/config.yaml, horaires_crc) — jamais deviné par le modèle de
langage. Utilisé par le webhook de personnalisation (assistant/api/
main.py) pour transmettre {{crc_ouvert}} à l'agent avant chaque appel,
au lieu de lui laisser inférer l'état du CRC à partir de l'heure système
seule (voir docs/prochaines-etapes.md, 30/10/2026).

Jours fériés français calculés, jamais une liste figée à mettre à jour
chaque année (voir _jours_feries) — fixes plus mobiles (calculés à
partir de Pâques, algorithme de Meeus/Jones/Butcher, grégorien).
"""

from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from assistant.outils.horaires_theoriques import FUSEAU

RACINE = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = RACINE / "data" / "config.yaml"

_NOMS_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def _dimanche_de_paques(annee):
    """Algorithme de Meeus/Jones/Butcher (calendrier grégorien) — pas de
    table figée, valable pour n'importe quelle année."""
    a = annee % 19
    b, c = divmod(annee, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mois, jour = divmod(h + l - 7 * m + 114, 31)
    return date(annee, mois, jour + 1)


def _jours_feries(annee):
    """Jours fériés légaux français de l'année donnée — fixes et mobiles
    (calculés à partir de Pâques)."""
    paques = _dimanche_de_paques(annee)
    fixes = [
        date(annee, 1, 1), date(annee, 5, 1), date(annee, 5, 8),
        date(annee, 7, 14), date(annee, 8, 15), date(annee, 11, 1),
        date(annee, 11, 11), date(annee, 12, 25),
    ]
    mobiles = [
        paques + timedelta(days=1),   # lundi de Pâques
        paques + timedelta(days=39),  # Ascension
        paques + timedelta(days=50),  # lundi de Pentecôte
    ]
    return set(fixes + mobiles)


def _charger_horaires_crc():
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    return config["horaires_crc"]


def _mois_jour(valeur_mmdd):
    mois, jour = valeur_mmdd.split("-")
    return (int(mois), int(jour))


def _dans_saison(mois_jour, debut, fin):
    """debut/fin : tuples (mois, jour). Gère les saisons qui traversent
    le 31 décembre (ex. 10-01 → 03-31) : la saison est "à l'envers" si
    debut > fin, auquel cas la date est dans la saison si elle est
    après debut OU avant fin (jamais les deux à la fois)."""
    if debut <= fin:
        return debut <= mois_jour <= fin
    return mois_jour >= debut or mois_jour <= fin


def crc_ouvert_maintenant(maintenant=None):
    """True si le CRC est ouvert à cet instant (heure française). Sans
    argument, utilise l'heure actuelle — un instant explicite peut être
    passé pour les tests (voir tests/verifier_horaires_crc.py)."""
    maintenant = maintenant or datetime.now(FUSEAU)
    horaires = _charger_horaires_crc()

    nom_jour = _NOMS_JOURS[maintenant.weekday()]
    if nom_jour in horaires["jours_fermes_semaine"]:
        return False
    if maintenant.date() in _jours_feries(maintenant.year):
        return False

    mois_jour = (maintenant.month, maintenant.day)
    heure_actuelle = f"{maintenant.hour:02d}:{maintenant.minute:02d}"
    for saison in horaires["saisons"]:
        debut = _mois_jour(saison["debut"])
        fin = _mois_jour(saison["fin"])
        if _dans_saison(mois_jour, debut, fin):
            return saison["ouverture"] <= heure_actuelle < saison["fermeture"]

    # Aucune saison ne couvre cette date : configuration incomplète,
    # jamais une approximation — on considère le CRC fermé plutôt que
    # de deviner (CLAUDE.md, exactitude).
    return False
