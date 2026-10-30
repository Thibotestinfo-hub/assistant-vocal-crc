"""
Vérifie assistant.outils.horaires_crc contre des dates connues : jours
fériés fixes et mobiles, dimanche, bornes de saison, jours ouvrés dans
les horaires et en dehors. À rejouer à chaque modification de
data/config.yaml (horaires_crc) ou de la logique de calcul.

Usage : uv run python3 tests/verifier_horaires_crc.py
"""

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from assistant.outils.horaires_crc import _dimanche_de_paques, crc_ouvert_maintenant

FUSEAU = ZoneInfo("Europe/Paris")

CAS = [
    ("2026-10-30 10:00", True, "vendredi, saison hiver, dans les horaires"),
    ("2026-10-30 18:00", False, "vendredi, saison hiver, après 17h30"),
    ("2026-10-30 08:00", False, "vendredi, saison hiver, avant 8h30"),
    ("2026-11-01 10:00", False, "Toussaint, jour férié fixe"),
    ("2026-11-02 10:00", True, "lundi suivant la Toussaint, ouvert"),
    ("2026-11-08 10:00", False, "dimanche"),
    ("2026-07-14 10:00", False, "fête nationale, jour férié fixe"),
    ("2026-07-15 10:00", True, "mercredi, saison été, dans les horaires"),
    ("2026-07-15 19:00", False, "mercredi, saison été, après 18h"),
    ("2026-04-06 10:00", False, "lundi de Pâques 2026 (mobile)"),
    ("2026-05-14 10:00", False, "Ascension 2026 (mobile)"),
    ("2026-05-25 10:00", False, "lundi de Pentecôte 2026 (mobile)"),
    ("2026-04-01 10:00", True, "1er avril, bascule vers la saison été"),
    ("2026-03-31 10:00", True, "31 mars, dernier jour de la saison hiver"),
    ("2027-01-01 10:00", False, "jour de l'an (changement d'année)"),
]


def verifier():
    assert _dimanche_de_paques(2026).isoformat() == "2026-04-05", "Pâques 2026 attendu au 05/04"

    echecs = 0
    for horodatage, attendu, label in CAS:
        dt = datetime.fromisoformat(horodatage).replace(tzinfo=FUSEAU)
        obtenu = crc_ouvert_maintenant(dt)
        statut = "OK  " if obtenu == attendu else "FAIL"
        if obtenu != attendu:
            echecs += 1
        print(f"[{statut}] {horodatage}  attendu={attendu!s:5}  obtenu={obtenu!s:5}  ({label})")

    print(f"\n{len(CAS) - echecs}/{len(CAS)} vérifications passées.")
    return echecs == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if verifier() else 1)
