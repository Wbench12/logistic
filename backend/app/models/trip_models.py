import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from enum import Enum

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .company_models import Company, Vehicle

# ============= CARGO ENUMS =============
class CargoCategory(str, Enum):
    # Agroalimentaire
    A01 = "a01_produits_frais"
    A02 = "a02_produits_surgeles"
    A03 = "a03_produits_secs"
    A04 = "a04_boissons_liquides"
    A05 = "a05_produits_agricoles_bruts"
    A06 = "a06_produits_transformes"
    
    # Construction
    B01 = "b01_materiaux_vrac"
    B02 = "b02_materiaux_solides"
    B03 = "b03_beton_pret"
    B04 = "b04_bois_charpente"
    B05 = "b05_materiaux_lourds"
    
    # Industrial
    I01 = "i01_produits_finis"
    I02 = "i02_pieces_detachees"
    I03 = "i03_produits_metalliques"
    I04 = "i04_emballages_palettes"
    I05 = "i05_produits_sensibles"
    
    # Chemical
    C01 = "c01_chimiques_liquides"
    C02 = "c02_chimiques_solides"
    C03 = "c03_gaz_industriels"
    C04 = "c04_hydrocarbures"
    C05 = "c05_dechets_dangereux"
    
    # Add more as per Liste 02...

class MaterialType(str, Enum):
    SOLID = "solide"
    LIQUID = "liquide"
    GAS = "gaz"

class TripStatus(str, Enum):
    PLANNED = "planifie"
    IN_PROGRESS = "en_cours"
    COMPLETED = "termine"
    CANCELLED = "annule"

# ============= TRIP MODELS =============
class TripBase(SQLModel):
    departure_point: str = Field(max_length=255)
    departure_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    departure_lng: Optional[float] = Field(default=None, ge=-180, le=180)
    
    arrival_point: str = Field(max_length=255)
    arrival_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    arrival_lng: Optional[float] = Field(default=None, ge=-180, le=180)
    
    departure_datetime: datetime
    arrival_datetime_planned: datetime
    arrival_datetime_actual: Optional[datetime] = None
    
    cargo_category: CargoCategory
    material_type: MaterialType
    cargo_weight_kg: float = Field(gt=0)
    
    driver_name: Optional[str] = Field(default=None, max_length=255)
    status: TripStatus = TripStatus.PLANNED
    
    # Calculated fields (will be populated by service)
    distance_km: Optional[float] = Field(default=None, ge=0)
    duration_minutes: Optional[int] = Field(default=None, ge=0)
    return_distance_km: Optional[float] = Field(default=None, ge=0)
    
    notes: Optional[str] = Field(default=None, max_length=1000)

class TripCreate(TripBase):
    vehicle_id: uuid.UUID

class TripUpdate(SQLModel):
    departure_point: Optional[str] = Field(default=None, max_length=255)
    arrival_point: Optional[str] = Field(default=None, max_length=255)
    departure_datetime: Optional[datetime] = None
    arrival_datetime_planned: Optional[datetime] = None
    arrival_datetime_actual: Optional[datetime] = None
    cargo_category: Optional[CargoCategory] = None
    material_type: Optional[MaterialType] = None
    cargo_weight_kg: Optional[float] = Field(default=None, gt=0)
    driver_name: Optional[str] = Field(default=None, max_length=255)
    status: Optional[TripStatus] = None
    notes: Optional[str] = Field(default=None, max_length=1000)

class Trip(TripBase, table=True):
    __tablename__: str = "trips"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Foreign Keys
    company_id: uuid.UUID = Field(foreign_key="companies.id", nullable=False)
    vehicle_id: uuid.UUID = Field(foreign_key="vehicles.id", nullable=False)
    
    # For optimization results
    optimization_batch_id: Optional[uuid.UUID] = Field(default=None, index=True)
    assigned_vehicle_id: Optional[uuid.UUID] = Field(default=None)  # After optimization
    sequence_order: Optional[int] = None  # Order in chain
    is_last_in_chain: bool = False
    
    # Relationships
    company: "Company" = Relationship(back_populates="trips")
    vehicle: "Vehicle" = Relationship(back_populates="trips")

class TripPublic(TripBase):
    id: uuid.UUID
    company_id: uuid.UUID
    vehicle_id: uuid.UUID
    created_at: datetime
    optimization_batch_id: Optional[uuid.UUID]

class TripsPublic(SQLModel):
    data: list[TripPublic]
    count: int

# ============= OPTIMIZATION MODELS =============
class OptimizationBatchStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class OptimizationBatch(SQLModel, table=True):
    __tablename__: str = "optimization_batches"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    batch_date: datetime = Field(index=True)
    status: OptimizationBatchStatus = OptimizationBatchStatus.PENDING
    
    # Metrics
    total_trips: int = 0
    km_saved: Optional[float] = None
    fuel_saved_liters: Optional[float] = None
    vehicles_used: Optional[int] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Solver details
    solver_time_seconds: Optional[float] = None
    solver_status: Optional[str] = None

class OptimizationBatchPublic(SQLModel):
    id: uuid.UUID
    batch_date: datetime
    status: OptimizationBatchStatus
    total_trips: int
    km_saved: Optional[float]
    fuel_saved_liters: Optional[float]
    created_at: datetime

# ============= DASHBOARD METRICS =============
class DashboardMetrics(SQLModel):
    """Response model for dashboard KPIs"""
    trips_in_progress: int
    vehicles_distributed: int
    km_reduced_today: float
    fuel_saved_today: float
    daily_trips: list[TripPublic]
    esg_contribution: dict  # CO2 saved, etc.