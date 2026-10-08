"""
Contrats JSON de chaque outil, tels que définis dans
docs/spec-assistant-vocal-v0-revisee.md, §4. FastAPI s'en sert pour
valider les requêtes et générer la documentation automatique (/docs).
"""

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

# Un min_length=1 ne suffit pas : un modèle peut inventer une valeur non
# vide mais fictive plutôt que de poser la question ("0000000000", vu le
# 28/09/2026 avec Gemini 3.1 Flash Lite sur enregistrer_objet_perdu — voir
# docs/prochaines-etapes.md). On valide donc la forme d'un vrai numéro
# français : 10 chiffres, commence par 0, le deuxième chiffre n'est pas 0.
_RE_TELEPHONE = re.compile(r"0[1-9]\d{8}$")


def _valider_telephone(valeur: str) -> str:
    nettoye = re.sub(r"[ .\-]", "", valeur)
    if not _RE_TELEPHONE.fullmatch(nettoye):
        raise ValueError("numéro de téléphone invalide (attendu : 10 chiffres, format français)")
    return valeur


# --- rechercher_information ---

class InformationRequete(BaseModel):
    question: str
    categorie: Optional[Literal[
        "tarifs", "agences", "conditions", "accessibilite", "tad", "vls", "procedures", "amendes",
    ]] = None


class InformationReponse(BaseModel):
    trouve: bool
    reponse_source: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    maj: Optional[str] = None
    confiance: Optional[Literal["haute", "moyenne", "basse"]] = None


# --- rechercher_arret ---

class RechercherArretRequete(BaseModel):
    texte: str
    commune: Optional[str] = None
    ligne: Optional[str] = None


class CandidatArret(BaseModel):
    arret_id: str
    nom: str
    commune: str
    lignes: list[str]
    score: float


class RechercherArretReponse(BaseModel):
    confiance: Literal["haute", "moyenne", "basse"]
    candidats: list[CandidatArret]


# --- horaires_theoriques ---

class HorairesRequete(BaseModel):
    arret_id: str
    ligne: Optional[str] = None
    direction: Optional[str] = None
    type: Literal["prochains", "premier", "dernier", "circulation", "creneau"] = "prochains"
    date: Optional[str] = None
    nb: int = 3
    heure_debut: Optional[str] = None  # "HH:MM", avec type="creneau" uniquement
    heure_fin: Optional[str] = None    # "HH:MM", avec type="creneau" uniquement


class Depart(BaseModel):
    ligne: str
    destination: Optional[str]
    heure: str
    dans_minutes: Optional[int]


class HorairesReponse(BaseModel):
    type_service: Optional[str] = None
    circule_aujourdhui: Optional[bool] = None
    departs: Optional[list[Depart]] = None
    premier: Optional[str] = None
    dernier: Optional[str] = None
    erreur: Optional[str] = None


# --- enregistrer_objet_perdu ---

class ObjetPerduRequete(BaseModel):
    nature: str
    description: str
    ligne: Optional[str] = None
    sens: Optional[str] = None
    date_perte: str
    creneau_horaire: str
    lieu: Literal["a_bord", "arret", "agence", "incertain"]
    arret_id: Optional[str] = None
    # min_length=1 : sans ça, rien n'empêche un modèle d'appeler l'outil
    # avant d'avoir demandé nom/téléphone à l'appelant (bug GPT-6 Luna du
    # 28/09/2026, voir docs/prochaines-etapes.md) — la validation renvoie
    # une 422 plutôt que d'enregistrer une déclaration inexploitable.
    nom: str = Field(min_length=1)
    telephone: str = Field(min_length=1)
    email: Optional[str] = None
    opt_in_marketing: bool

    _valider = field_validator("telephone")(_valider_telephone)


class ObjetPerduReponse(BaseModel):
    succes: bool
    declaration_id: Optional[int] = None
    erreur: Optional[str] = None


# --- demander_rappel ---

class RappelRequete(BaseModel):
    telephone: str = Field(min_length=1)
    nom: Optional[str] = None
    email: Optional[str] = None
    motif: Literal[
        "amende", "reclamation", "tad", "scolaire", "hors_perimetre", "demande_agent",
        "abonnement", "velo",
    ]
    resume: str

    _valider = field_validator("telephone")(_valider_telephone)
    opt_in_marketing: bool = False
    # Optionnel : fourni par ElevenLabs via {{system__conversation_id}} si
    # câblé côté configuration de l'agent (voir assistant/outils/rappels.py)
    # — permet de relier la demande à l'appel dans le back-office.
    conversation_id: Optional[str] = None


class RappelReponse(BaseModel):
    succes: bool
    demande_id: Optional[int] = None
    erreur: Optional[str] = None


# --- transferer_agent ---

class TransfertRequete(BaseModel):
    motif: str
    resume: str


class TransfertReponse(BaseModel):
    succes: bool
    transfert_id: int


# --- enregistrer_satisfaction ---
# conversation_id : fourni par ElevenLabs via la variable dynamique
# {{system__conversation_id}}, à déclarer dans la configuration de
# l'outil côté agent (voir assistant/outils/satisfaction.py).

class SatisfactionRequete(BaseModel):
    conversation_id: str
    satisfait: bool


class SatisfactionReponse(BaseModel):
    succes: bool


# --- rechercher_repere (expérimental, voir docs/prochaines-etapes.md) ---

class RepereRequete(BaseModel):
    texte: str
    commune: Optional[str] = None


class CandidatRepere(BaseModel):
    commune: str
    libelle: str
    arret_id: str
    arret_nom: str
    distance_km: float


class RepereReponse(BaseModel):
    candidats: list[CandidatRepere]


# --- calculer_itineraire (expérimental, voir docs/prochaines-etapes.md) ---

class ItineraireRequete(BaseModel):
    arret_depart_id: str
    arret_arrivee_id: str
    date: Optional[str] = None
    heure: Optional[str] = None


class EtapeItineraire(BaseModel):
    ligne: Optional[str] = None
    destination: Optional[str] = None
    depart: Optional[str] = None
    arrivee: Optional[str] = None
    arret_correspondance: Optional[str] = None
    commune_correspondance: Optional[str] = None


class ItineraireReponse(BaseModel):
    trouve: bool
    type: Optional[Literal["direct", "correspondance"]] = None
    etapes: Optional[list[EtapeItineraire]] = None
    jour_decale: Optional[int] = None
    erreur: Optional[str] = None


# --- calculer_itineraire_complexe (expérimental, API Google Routes,
# voir docs/prochaines-etapes.md 08/10/2026 et assistant/outils/
# itineraire_google.py) : uniquement en repli quand calculer_itineraire
# ne trouve rien (plus d'une correspondance, ou trajet nécessitant de la
# marche) — jamais les deux pour le même trajet. ---

class ItineraireComplexeRequete(BaseModel):
    arret_depart_id: str
    arret_arrivee_id: str
    date: Optional[str] = None
    heure: Optional[str] = None


class EtapeItineraireComplexe(BaseModel):
    type: Literal["marche", "transport"]
    ligne: Optional[str] = None
    mode: Optional[str] = None
    destination: Optional[str] = None
    arret_depart: Optional[str] = None
    arret_arrivee: Optional[str] = None
    depart: Optional[str] = None
    arrivee: Optional[str] = None


class ItineraireComplexeReponse(BaseModel):
    trouve: bool
    etapes: Optional[list[EtapeItineraireComplexe]] = None
    duree_totale_min: Optional[int] = None
    erreur: Optional[str] = None
