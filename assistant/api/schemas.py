"""
Contrats JSON de chaque outil, tels que définis dans
docs/spec-assistant-vocal-v0-revisee.md, §4. FastAPI s'en sert pour
valider les requêtes et générer la documentation automatique (/docs).
"""

from typing import Literal, Optional

from pydantic import BaseModel


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
    type: Literal["prochains", "premier", "dernier", "circulation"] = "prochains"
    date: Optional[str] = None
    nb: int = 3


class Depart(BaseModel):
    ligne: str
    destination: Optional[str]
    heure: str
    dans_minutes: Optional[int]


class HorairesReponse(BaseModel):
    type_service: str
    circule_aujourdhui: bool
    departs: list[Depart]
    premier: Optional[str]
    dernier: Optional[str]


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
    nom: str
    telephone: str
    email: Optional[str] = None
    opt_in_marketing: bool


class ObjetPerduReponse(BaseModel):
    succes: bool
    declaration_id: Optional[int] = None
    erreur: Optional[str] = None


# --- demander_rappel ---

class RappelRequete(BaseModel):
    telephone: str
    nom: Optional[str] = None
    email: Optional[str] = None
    motif: Literal["amende", "reclamation", "tad", "scolaire", "hors_perimetre", "demande_agent"]
    resume: str
    opt_in_marketing: bool = False


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
