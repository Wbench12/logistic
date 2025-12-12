import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from enum import Enum

from pydantic import field_validator
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .trip_models import Trip
    from .user_models import User

# ============= ENUMS =============
class CompanyType(str, Enum):
    PRODUCTION = "production"
    TRADING = "negoce"
    SERVICE = "service"

class PartnerType(str, Enum):
    COMPANY = "entreprise"
    LOGISTICS_PROVIDER = "prestataire_logistique"

class ActivitySector(str, Enum):
    AGROALIMENTAIRE = "agroalimentaire"
    CONSTRUCTION = "construction_btp"
    INDUSTRIAL = "industriel_manufacturier"
    CHEMICAL = "chimique_petrochimique"
    AGRICULTURAL = "agricole_rural"
    LOGISTICS = "logistique_messagerie"
    MEDICAL = "medical_parapharmaceutique"
    HYGIENE = "hygiene_dechets_environnement"
    ENERGY = "energie_ressources_naturelles"
    SPECIAL = "logistique_speciale"
    OTHER = "autre"

# ============= COMPANY MODELS =============
class CompanyBase(SQLModel):
    company_name: str = Field(
        max_length=255, 
        index=True,
        description="Nom officiel de l'entreprise"
    )
    nis: str = Field(
        max_length=15, 
        unique=True, 
        index=True,
        description="Numéro d'Identification Statistique (NIS) - Maximum 15 chiffres"
    )
    nif: str = Field(
        min_length=15, 
        max_length=20, 
        unique=True, 
        index=True,
        description="Numéro d'Identification Fiscale (NIF) - Entre 15 et 20 chiffres"
    )
    headquarters_address: str = Field(
        max_length=500,
        description="Adresse complète du siège social"
    )
    company_type: CompanyType
    activity_sector: ActivitySector
    sector_specification: Optional[str] = Field(
        default=None, 
        max_length=255,
        description="Précision sur le secteur d'activité"
    )
    partner_type: PartnerType
    legal_representative_name: str = Field(
        max_length=255,
        description="Nom complet du représentant légal"
    )
    legal_representative_contact: str = Field(
        max_length=50,
        description="Numéro de téléphone algérien (format: +213XXXXXXXXX)"
    )
    logo_url: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True
    is_verified: bool = False

    @field_validator('nis')
    @classmethod
    def validate_nis(cls, v: str) -> str:
        if not v:
            raise ValueError("Le NIS est obligatoire")
        if not v.isdigit():
            raise ValueError("Le NIS doit contenir uniquement des chiffres")
        if len(v) > 15:
            raise ValueError("Le NIS ne peut pas dépasser 15 chiffres")
        return v

    @field_validator('nif')
    @classmethod
    def validate_nif(cls, v: str) -> str:
        if not v:
            raise ValueError("Le NIF est obligatoire")
        if not v.isdigit():
            raise ValueError("Le NIF doit contenir uniquement des chiffres")
        if len(v) < 15:
            raise ValueError("Le NIF doit contenir au moins 15 chiffres")
        if len(v) > 20:
            raise ValueError("Le NIF ne peut pas dépasser 20 chiffres")
        return v

    @field_validator('legal_representative_contact')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not v:
            raise ValueError("Le numéro de téléphone est obligatoire")
        # Remove spaces and hyphens for validation
        cleaned = v.replace(" ", "").replace("-", "")
        if not cleaned.startswith("+213") and not cleaned.startswith("0"):
            raise ValueError("Le numéro doit être au format algérien (+213 ou 0)")
        # Check if remaining chars are digits
        digits = cleaned.lstrip("+213").lstrip("0")
        if not digits.isdigit():
            raise ValueError("Le numéro de téléphone contient des caractères invalides")
        if len(digits) < 9 or len(digits) > 10:
            raise ValueError("Le numéro de téléphone doit contenir 9 ou 10 chiffres")
        return v

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(SQLModel):
    company_name: Optional[str] = Field(default=None, max_length=255)
    headquarters_address: Optional[str] = Field(default=None, max_length=500)
    company_type: Optional[CompanyType] = None
    activity_sector: Optional[ActivitySector] = None
    sector_specification: Optional[str] = Field(default=None, max_length=255)
    partner_type: Optional[PartnerType] = None
    legal_representative_name: Optional[str] = Field(default=None, max_length=255)
    legal_representative_contact: Optional[str] = Field(default=None, max_length=50)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None

class Company(CompanyBase, table=True):
    __tablename__: str = "companies"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    user: "User" = Relationship(back_populates="companies")
    vehicles: list["Vehicle"] = Relationship(back_populates="company", cascade_delete=True)
    trips: list["Trip"] = Relationship(back_populates="company", cascade_delete=True)

class CompanyPublic(CompanyBase):
    id: uuid.UUID
    created_at: datetime
    user_id: uuid.UUID

# ============= VEHICLE MODELS =============
class VehicleCategory(str, Enum):
    # Agroalimentaire
    AG1 = "ag1_camion_frigorifique"
    AG2 = "ag2_camion_refrigere"
    AG3 = "ag3_camion_isotherme"
    AG4 = "ag4_camion_citerne_alimentaire"
    AG5 = "ag5_camionnette_distribution"
    AG6 = "ag6_camion_plateau_fruits"
    
    # Construction
    BT1 = "bt1_camion_benne"
    BT2 = "bt2_semi_remorque_benne"
    BT3 = "bt3_camion_malaxeur"
    BT4 = "bt4_camion_plateau_ridelles"
    BT5 = "bt5_porte_engins"
    BT6 = "bt6_camion_citerne_eau"
    
    # Industrial
    IN1 = "in1_camion_bache"
    IN2 = "in2_fourgon_ferme"
    IN3 = "in3_camion_grue"
    IN4 = "in4_porte_conteneurs"
    IN5 = "in5_camion_plateau_surbaisse"
    IN6 = "in6_camion_fourgon_hayon"
    
    # Chemical
    CH1 = "ch1_camion_citerne_hydrocarbures"
    CH2 = "ch2_camion_citerne_chimique"
    CH3 = "ch3_camion_citerne_gaz"
    CH4 = "ch4_camion_adr"
    CH5 = "ch5_camion_cuve_calorifugee"
    
    # Add more categories as needed...

class VehicleStatus(str, Enum):
    AVAILABLE = "disponible"
    IN_MISSION = "en_mission"
    MAINTENANCE = "maintenance"
    INACTIVE = "inactif"

class VehicleBase(SQLModel):
    license_plate: str = Field(max_length=20, unique=True, index=True)
    category: VehicleCategory
    capacity_tons: Optional[float] = Field(default=None, ge=0)
    capacity_m3: Optional[float] = Field(default=None, ge=0)
    status: VehicleStatus = VehicleStatus.AVAILABLE
    current_km: float = Field(default=0, ge=0)
    last_technical_control: Optional[datetime] = None
    insurance_expiry: Optional[datetime] = None
    is_active: bool = True
    
    # Technical details
    year: Optional[int] = Field(default=None, ge=1900, le=2100)
    brand: Optional[str] = Field(default=None, max_length=100)
    model: Optional[str] = Field(default=None, max_length=100)
    fuel_type: Optional[str] = Field(default=None, max_length=50)

class VehicleCreate(VehicleBase):
    company_id: uuid.UUID

class VehicleUpdate(SQLModel):
    category: Optional[VehicleCategory] = None
    capacity_tons: Optional[float] = Field(default=None, ge=0)
    capacity_m3: Optional[float] = Field(default=None, ge=0)
    status: Optional[VehicleStatus] = None
    current_km: Optional[float] = Field(default=None, ge=0)
    last_technical_control: Optional[datetime] = None
    insurance_expiry: Optional[datetime] = None
    is_active: Optional[bool] = None
    year: Optional[int] = Field(default=None, ge=1900, le=2100)
    brand: Optional[str] = Field(default=None, max_length=100)
    model: Optional[str] = Field(default=None, max_length=100)
    fuel_type: Optional[str] = Field(default=None, max_length=50)

class Vehicle(VehicleBase, table=True):
    __tablename__ = "vehicles"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Foreign Keys
    company_id: uuid.UUID = Field(foreign_key="companies.id", nullable=False)
    
    # Relationships
    company: Company = Relationship(back_populates="vehicles")
    trips: list["Trip"] = Relationship(back_populates="vehicle")

class VehiclePublic(VehicleBase):
    id: uuid.UUID
    company_id: uuid.UUID
    created_at: datetime

class VehiclesPublic(SQLModel):
    data: list[VehiclePublic]
    count: int