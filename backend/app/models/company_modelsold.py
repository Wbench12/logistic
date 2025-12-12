# from enum import Enum
# from typing import List, Optional, Dict, Any
# from pydantic import EmailStr
# from sqlalchemy import Column, JSON
# from sqlmodel import Field, Relationship, SQLModel
# import uuid
# from .user_models import User

# class BusinessType(str, Enum):
#     PRODUCTION = "production"
#     TRADING = "negoce"
#     SERVICE = "service"

# class Sector(str, Enum):
#     AGROALIMENTAIRE = "agroalimentaire"
#     CONSTRUCTION_BTP = "construction_btp"
#     INDUSTRIEL_MANUFACTURIER = "industriel_manufacturier"
#     CHIMIQUE_PETROCHIMIQUE = "chimique_petrochimique"
#     AGRICOLE_RURAL = "agricole_rural"
#     LOGISTIQUE_MESSAGERIE = "logistique_messagerie"
#     MEDICAL_PARAPHARMACEUTIQUE = "medical_parapharmaceutique"
#     HYGIENE_DECHETS_ENVIRONNEMENT = "hygiene_dechets_environnement"
#     ENERGIE_RESSOURCES_NATURELLES = "energie_ressources_naturelles"
#     LOGISTIQUE_SPECIALE = "logistique_speciale"
#     AUTRE = "autre"

# class PartnerType(str, Enum):
#     ENTERPRISE = "entreprise"
#     LOGISTICS_PROVIDER = "prestataire_logistique"

# class Company(SQLModel, table=True):
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     owner_id: uuid.UUID = Field(foreign_key="user.id")
#     name: str = Field(max_length=255)
#     nis: str = Field(max_length=15)
#     nif: str = Field(max_length=20)
#     headquarters_address: str
#     business_type: BusinessType
#     business_type_specification: Optional[str] = Field(default=None)
#     sector: Sector
#     partner_type: PartnerType
#     legal_representative_name: str
#     legal_representative_contact: str
#     logo_url: Optional[str] = Field(default=None)
#     professional_email: EmailStr
#     phone_number: str
#     is_verified: bool = Field(default=False)
#     created_at: Any = Field(default_factory=lambda: None)
#     owner: "User" = Relationship(back_populates="companies")  # type: ignore[name-defined]
#     vehicles: List["Vehicle"] = Relationship(back_populates="company")  # type: ignore[name-defined]
#     trips: List["Trip"] = Relationship(back_populates="company")  # type: ignore[name-defined]
#     optimization_jobs: List["OptimizationJob"] = Relationship(back_populates="company")  # type: ignore[name-defined]

# class CompanyCreate(SQLModel):
#     name: str
#     nis: str
#     nif: str
#     headquarters_address: str
#     business_type: BusinessType
#     business_type_specification: Optional[str] = None
#     sector: Sector
#     partner_type: PartnerType
#     legal_representative_name: str
#     legal_representative_contact: str
#     professional_email: EmailStr
#     phone_number: str
