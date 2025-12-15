import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List, Dict, ClassVar
from enum import Enum

from sqlmodel import Field, Relationship, SQLModel, Column
from sqlalchemy.dialects.postgresql import JSON
from pydantic import field_validator

from .company_models import VehicleCategory

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
    cargo_volume_m3: Optional[float] = Field(
        default=None,
        gt=0,
        description="Volume in cubic meters",
    )
    
    driver_name: Optional[str] = Field(default=None, max_length=255)
    status: TripStatus = TripStatus.PLANNED
    
    # Calculated fields (will be populated by service)
    distance_km: Optional[float] = Field(default=None, ge=0)
    duration_minutes: Optional[int] = Field(default=None, ge=0)
    
    notes: Optional[str] = Field(default=None, max_length=1000)
    
    # New: Routing fields for Valhalla
    route_polyline: Optional[str] = Field(default=None)
    route_distance_km: Optional[float] = Field(default=None, ge=0)
    route_duration_min: Optional[int] = Field(default=None, ge=0)
    estimated_arrival_datetime: Optional[datetime] = None
    
    # Return route to depot
    return_route_polyline: Optional[str] = Field(default=None)
    return_distance_km: Optional[float] = Field(default=None, ge=0)
    return_duration_min: Optional[int] = Field(default=None, ge=0)
    
    # Time windows for optimization
    loading_window_start: Optional[datetime] = None
    loading_window_end: Optional[datetime] = None
    delivery_window_start: Optional[datetime] = None
    delivery_window_end: Optional[datetime] = None
    
    # Trip constraints
    hazardous_material: bool = False
    temperature_requirement_celsius: Optional[float] = None
    trip_priority: int = Field(default=1, ge=1, le=5)

    # Vehicle requirements (when no concrete vehicle is assigned yet)
    required_vehicle_category: Optional[VehicleCategory] = None
    
    # Date tracking
    trip_date: Optional[datetime] = Field(
        default=None,
        description="The date of the trip (extracted from departure_datetime)"
    )
    uploaded_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="When this trip was uploaded to the system"
    )
    
    # Route calculation status
    route_calculated: bool = False
    optimization_status: str = Field(default="pending")  # pending, assigned, completed
    
    # Map creation fields
    created_from_map: bool = False
    map_session_id: Optional[str] = Field(default=None, max_length=50)

    @field_validator('trip_date', mode='before')
    @classmethod
    def set_trip_date(cls, v, info):
        """Automatically set trip_date from departure_datetime."""
        if v is None:
            # Get departure_datetime from the data
            departure_datetime = info.data.get('departure_datetime')
            if departure_datetime:
                # Extract just the date part
                if isinstance(departure_datetime, datetime):
                    return departure_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        return v

class TripCreate(TripBase):
    vehicle_id: Optional[uuid.UUID] = None

class TripUpdate(SQLModel):
    departure_point: Optional[str] = Field(default=None, max_length=255)
    arrival_point: Optional[str] = Field(default=None, max_length=255)
    departure_datetime: Optional[datetime] = None
    arrival_datetime_planned: Optional[datetime] = None
    arrival_datetime_actual: Optional[datetime] = None
    cargo_category: Optional[CargoCategory] = None
    material_type: Optional[MaterialType] = None
    cargo_weight_kg: Optional[float] = Field(default=None, gt=0)
    cargo_volume_m3: Optional[float] = Field(default=None, gt=0)
    driver_name: Optional[str] = Field(default=None, max_length=255)
    status: Optional[TripStatus] = None
    notes: Optional[str] = Field(default=None, max_length=1000)
    route_polyline: Optional[str] = None
    route_distance_km: Optional[float] = Field(default=None, ge=0)
    route_duration_min: Optional[int] = Field(default=None, ge=0)
    estimated_arrival_datetime: Optional[datetime] = None
    loading_window_start: Optional[datetime] = None
    loading_window_end: Optional[datetime] = None
    delivery_window_start: Optional[datetime] = None
    delivery_window_end: Optional[datetime] = None
    hazardous_material: Optional[bool] = None
    temperature_requirement_celsius: Optional[float] = None
    trip_priority: Optional[int] = Field(default=None, ge=1, le=5)

    vehicle_id: Optional[uuid.UUID] = None
    required_vehicle_category: Optional[VehicleCategory] = None

class Trip(TripBase, table=True):
    __tablename__: ClassVar[str] = "trips"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Foreign Keys
    company_id: uuid.UUID = Field(foreign_key="companies.id", nullable=False)
    vehicle_id: Optional[uuid.UUID] = Field(default=None, foreign_key="vehicles.id", nullable=True)
    
    # For optimization results
    optimization_batch_id: Optional[uuid.UUID] = Field(default=None, index=True)
    assigned_vehicle_id: Optional[uuid.UUID] = Field(default=None)  # After optimization
    sequence_order: Optional[int] = None  # Order in chain
    is_last_in_chain: bool = False
    
    # Relationships
    company: "Company" = Relationship(back_populates="trips")
    vehicle: Optional["Vehicle"] = Relationship(back_populates="trips")

class TripPublic(TripBase):
    id: uuid.UUID
    company_id: uuid.UUID
    vehicle_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    optimization_batch_id: Optional[uuid.UUID]
    assigned_vehicle_id: Optional[uuid.UUID]
    sequence_order: Optional[int]
    is_last_in_chain: bool

class TripsPublic(SQLModel):
    data: list[TripPublic]
    count: int

# ============= MAP MARKER MODEL =============
class MapMarker(SQLModel, table=True):
    __tablename__: ClassVar[str] = "map_markers"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="companies.id")
    name: str = Field(max_length=255)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    marker_type: str = Field(default="depot")  # depot, warehouse, customer, etc.
    address: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

# ============= OPTIMIZATION MODELS =============
class OptimizationBatchStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class OptimizationBatch(SQLModel, table=True):
    __tablename__: ClassVar[str] = "optimization_batches"
    
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
    
    # Cross-company optimization fields
    optimization_type: str = Field(default="single_company")  # single_company, cross_company
    participating_companies: Optional[List[uuid.UUID]] = Field(default=None, sa_column=Column(JSON))
    
    # KPI summary
    total_companies: int = 0
    total_vehicles_shared: int = 0
    total_km_saved: float = 0.0
    total_fuel_saved: float = 0.0
    
    # Results storage
    company_results: Optional[Dict] = Field(default=None, sa_column=Column(JSON))

class OptimizationBatchPublic(SQLModel):
    id: uuid.UUID
    batch_date: datetime
    status: OptimizationBatchStatus
    total_trips: int
    km_saved: Optional[float]
    fuel_saved_liters: Optional[float]
    created_at: datetime
    optimization_type: str
    total_companies: int
    total_km_saved: float
    total_fuel_saved: float

# ============= COMPANY OPTIMIZATION RESULT MODEL =============
class CompanyOptimizationResult(SQLModel, table=True):
    __tablename__: ClassVar[str] = "company_optimization_results"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    optimization_batch_id: uuid.UUID = Field(foreign_key="optimization_batches.id")
    company_id: uuid.UUID = Field(foreign_key="companies.id")
    
    # KPI metrics
    trips_contributed: int = 0  # Trips this company submitted
    trips_assigned: int = 0  # Trips assigned to this company's vehicles
    vehicles_used: int = 0
    vehicles_shared_out: int = 0  # This company's vehicles used by others
    vehicles_borrowed: int = 0  # Other companies' vehicles used by this company
    
    # Efficiency metrics
    km_saved: float = 0.0
    fuel_saved_liters: float = 0.0
    co2_saved_kg: float = 0.0
    cost_saved_usd: float = 0.0
    
    # Chain metrics
    chains_participated: int = 0
    average_chain_length: float = 0.0
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ============= DASHBOARD METRICS =============
class DashboardMetrics(SQLModel):
    """Response model for dashboard KPIs"""
    trips_in_progress: int
    vehicles_distributed: int
    km_reduced_today: float
    fuel_saved_today: float
    daily_trips: list[TripPublic]
    esg_contribution: dict  # CO2 saved, etc.