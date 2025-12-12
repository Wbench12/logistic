# import uuid
# from datetime import datetime
# from typing import List, Optional, Dict, Any
# from enum import Enum

# from pydantic import EmailStr
# from sqlalchemy import Column, JSON
# from sqlmodel import Field, Relationship, SQLModel


# # Shared properties
# class UserBase(SQLModel):
#     email: EmailStr = Field(index=True, max_length=255)
#     is_active: bool = True
#     is_superuser: bool = False
#     full_name: Optional[str] = Field(default=None, max_length=255)


# # Properties to receive via API on creation
# class UserCreate(UserBase):
#     password: str = Field(min_length=8, max_length=128)


# class UserRegister(SQLModel):
#     email: EmailStr = Field(max_length=255)
#     password: str = Field(min_length=8, max_length=128)
#     full_name: Optional[str] = Field(default=None, max_length=255)


# # Properties to receive via API on update, all are optional
# class UserUpdate(UserBase):
#     email: Optional[EmailStr] = Field(default=None, max_length=255)  # type: ignore
#     password: Optional[str] = Field(default=None, min_length=8, max_length=128)


# class UserUpdateMe(SQLModel):
#     full_name: Optional[str] = Field(default=None, max_length=255)
#     email: Optional[EmailStr] = Field(default=None, max_length=255)


# class UpdatePassword(SQLModel):
#     current_password: str = Field(min_length=8, max_length=128)
#     new_password: str = Field(min_length=8, max_length=128)


# # Database model, database table inferred from class name
# class User(UserBase, table=True):
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     hashed_password: str

#     # relationships
#     companies: List["Company"] = Relationship(back_populates="owner")
#     optimization_jobs: List["OptimizationJob"] = Relationship(back_populates="owner")


# # Properties to return via API, id is always required
# class UserPublic(UserBase):
#     id: uuid.UUID


# class UsersPublic(SQLModel):
#     data: List[UserPublic]
#     count: int


# # Enums for Logistics Platform

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


# class VehicleStatus(str, Enum):
#     AVAILABLE = "disponible"
#     ON_MISSION = "en_mission"
#     MAINTENANCE = "maintenance"


# class VehicleState(str, Enum):
#     ACTIVE = "actif"
#     INACTIVE = "inactif"


# class TripStatus(str, Enum):
#     PLANNED = "planifié"
#     IN_PROGRESS = "en_cours"
#     COMPLETED = "terminé"
#     CANCELLED = "annulé"


# class MaterialType(str, Enum):
#     SOLID = "solide"
#     LIQUID = "liquide"
#     GAS = "gaz"


# class JobStatus(str, Enum):
#     PENDING = "PENDING"
#     RUNNING = "RUNNING"
#     COMPLETED = "COMPLETED"
#     INFEASIBLE = "INFEASIBLE"
#     FAILED = "FAILED"


# # Main Category Models

# class VehicleCategory(SQLModel, table=True):
#     id: str = Field(primary_key=True, max_length=10)  # e.g., "AG1", "BT1", "IN1"
#     name: str = Field(max_length=100)
#     sector: Sector
#     description: Optional[str] = Field(default=None)
#     main_use: Optional[str] = Field(default=None)
#     technical_constraints: Optional[str] = Field(default=None)
#     capacity_range: Optional[str] = Field(default=None)  # e.g., "10-20T", "5-15m³"
#     temperature_control: Optional[bool] = Field(default=False)
#     temperature_range: Optional[str] = Field(default=None)  # e.g., "0-6°C", "≤ -18°C"
#     requires_adr_certification: bool = Field(default=False)
#     requires_special_equipment: bool = Field(default=False)

#     vehicles: List["Vehicle"] = Relationship(back_populates="category")
#     optimization_groups: List["OptimizationGroup"] = Relationship(back_populates="vehicle_category")


# class ProductCategory(SQLModel, table=True):
#     id: str = Field(primary_key=True, max_length=10)  # e.g., "A01", "B01", "I01"
#     name: str = Field(max_length=100)
#     sector: Sector
#     description: Optional[str] = Field(default=None)
#     examples: Optional[str] = Field(default=None)
#     material_type: MaterialType
#     # use JSON column for recommended_vehicle_categories
#     recommended_vehicle_categories: List[str] = Field(
#         default_factory=list,
#         sa_column=Column(JSON),
#     )
#     requires_temperature_control: bool = Field(default=False)
#     temperature_range: Optional[str] = Field(default=None)
#     is_dangerous: bool = Field(default=False)
#     requires_special_handling: bool = Field(default=False)

#     trips: List["Trip"] = Relationship(back_populates="product_category")


# class OptimizationGroup(SQLModel, table=True):
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     name: str = Field(max_length=100)
#     sector: Sector
#     vehicle_category_id: str = Field(foreign_key="vehiclecategory.id")
#     description: Optional[str] = Field(default=None)
#     created_at: datetime = Field(default_factory=datetime.utcnow)

#     vehicle_category: Optional[VehicleCategory] = Relationship(back_populates="optimization_groups")
#     optimization_jobs: List["OptimizationJob"] = Relationship(back_populates="optimization_group")


# # Logistics Platform Models

# class Company(SQLModel, table=True):
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     owner_id: uuid.UUID = Field(foreign_key="user.id")
#     name: str = Field(max_length=255)
#     nis: str = Field(max_length=15)  # 15 digits
#     nif: str = Field(max_length=20)  # 15-20 characters
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
#     created_at: datetime = Field(default_factory=datetime.utcnow)

#     owner: User = Relationship(back_populates="companies")
#     vehicles: List["Vehicle"] = Relationship(back_populates="company")
#     trips: List["Trip"] = Relationship(back_populates="company")
#     optimization_jobs: List["OptimizationJob"] = Relationship(back_populates="company")


# class Vehicle(SQLModel, table=True):
#     id: str = Field(primary_key=True, max_length=50)  # License plate
#     company_id: uuid.UUID = Field(foreign_key="company.id")
#     category_id: str = Field(foreign_key="vehiclecategory.id")
#     depot_location: Optional[str] = Field(description="Depot location address or coordinates")
#     capacity: float = Field(description="Capacity in tons or m³")
#     current_status: VehicleStatus = Field(default=VehicleStatus.AVAILABLE)
#     state: VehicleState = Field(default=VehicleState.ACTIVE)
#     current_kilometers: float = Field(default=0.0)
#     last_technical_control: Optional[datetime] = Field(default=None)
#     last_insurance_check: Optional[datetime] = Field(default=None)

#     # Technical information
#     year: Optional[int] = Field(default=None)
#     brand: Optional[str] = Field(default=None)
#     model: Optional[str] = Field(default=None)
#     fuel_type: Optional[str] = Field(default=None)

#     created_at: datetime = Field(default_factory=datetime.utcnow)

#     company: Company = Relationship(back_populates="vehicles")
#     category: VehicleCategory = Relationship(back_populates="vehicles")
#     assignments: List["Assignment"] = Relationship(back_populates="vehicle")
#     maintenance_records: List["MaintenanceRecord"] = Relationship(back_populates="vehicle")
#     documents: List["VehicleDocument"] = Relationship(back_populates="vehicle")


# class Trip(SQLModel, table=True):
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     company_id: uuid.UUID = Field(foreign_key="company.id")
#     product_category_id: str = Field(foreign_key="productcategory.id")
#     reference: str = Field(description="Internal reference number")
#     start_point: str = Field(description="Start location address or coordinates")
#     end_point: str = Field(description="End location address or coordinates")
#     planned_start: datetime = Field(description="Planned start date/time")
#     planned_end: datetime = Field(description="Planned end date/time")
#     assigned_vehicle_id: Optional[str] = Field(default=None, foreign_key="vehicle.id")
#     assigned_driver: Optional[str] = Field(default=None)
#     status: TripStatus = Field(default=TripStatus.PLANNED)

#     # Optimization parameters
#     distance: Optional[float] = Field(default=None, description="Distance in km")
#     duration: Optional[int] = Field(default=None, description="Duration in minutes")
#     service_time: int = Field(default=0, description="Service time at destination in minutes")
#     demand: float = Field(description="Capacity demand in tons or m³")
#     return_to_depot_time: Optional[int] = Field(default=None, description="Return time to depot in minutes")

#     # Time windows for optimization (minutes from midnight)
#     earliest_start: int = Field(description="Earliest start time (minutes from midnight)")
#     latest_start: int = Field(description="Latest start time (minutes from midnight)")

#     created_at: datetime = Field(default_factory=datetime.utcnow)

#     company: Company = Relationship(back_populates="trips")
#     product_category: ProductCategory = Relationship(back_populates="trips")
#     assignments: List["Assignment"] = Relationship(back_populates="trip")


# class OptimizationJob(SQLModel, table=True):
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     owner_id: uuid.UUID = Field(foreign_key="user.id")
#     company_id: uuid.UUID = Field(foreign_key="company.id")
#     optimization_group_id: uuid.UUID = Field(foreign_key="optimizationgroup.id")
#     status: JobStatus = Field(default=JobStatus.PENDING)
#     objective: Optional[float] = Field(default=None)
#     config: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))  # type: ignore
#     metrics: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))  # type: ignore
#     diagnostics: List[str] = Field(default_factory=list, sa_column=Column(JSON))  # type: ignore
#     created_at: datetime = Field(default_factory=datetime.utcnow)
#     updated_at: datetime = Field(default_factory=datetime.utcnow)

#     owner: User = Relationship(back_populates="optimization_jobs")
#     company: Company = Relationship(back_populates="optimization_jobs")
#     optimization_group: OptimizationGroup = Relationship(back_populates="optimization_jobs")
#     assignments: List["Assignment"] = Relationship(back_populates="job")


# class Assignment(SQLModel, table=True):
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     job_id: uuid.UUID = Field(foreign_key="optimizationjob.id")
#     vehicle_id: str = Field(foreign_key="vehicle.id")
#     trip_id: uuid.UUID = Field(foreign_key="trip.id")
#     sequence_order: int = Field(description="Order in vehicle's route")
#     start_time: int = Field(description="Actual start time for this trip (minutes from midnight)")
#     end_time: int = Field(description="Actual end time for this trip (minutes from midnight)")
#     is_last: bool = Field(description="Whether this is the last trip for the vehicle")

#     job: OptimizationJob = Relationship(back_populates="assignments")
#     vehicle: Vehicle = Relationship(back_populates="assignments")
#     trip: Trip = Relationship(back_populates="assignments")


# class MaintenanceRecord(SQLModel, table=True):
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     vehicle_id: str = Field(foreign_key="vehicle.id")
#     maintenance_type: str
#     description: str
#     cost: Optional[float] = Field(default=None)
#     kilometers: float
#     maintenance_date: datetime
#     next_maintenance_date: Optional[datetime] = Field(default=None)
#     next_maintenance_kilometers: Optional[float] = Field(default=None)
#     created_at: datetime = Field(default_factory=datetime.utcnow)

#     vehicle: Vehicle = Relationship(back_populates="maintenance_records")


# class VehicleDocument(SQLModel, table=True):
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     vehicle_id: str = Field(foreign_key="vehicle.id")
#     document_type: str  # insurance, registration, technical_control, photos
#     file_url: str
#     file_name: str
#     upload_date: datetime = Field(default_factory=datetime.utcnow)
#     expiry_date: Optional[datetime] = Field(default=None)

#     vehicle: Vehicle = Relationship(back_populates="documents")


# # API Request/Response Models

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


# class VehicleCreate(SQLModel):
#     id: str
#     category_id: str
#     depot_location: str
#     capacity: float
#     year: Optional[int] = None
#     brand: Optional[str] = None
#     model: Optional[str] = None
#     fuel_type: Optional[str] = None


# class TripCreate(SQLModel):
#     reference: str
#     product_category_id: str
#     start_point: str
#     end_point: str
#     planned_start: datetime
#     planned_end: datetime
#     assigned_driver: Optional[str] = None
#     demand: float
#     service_time: int = 0
#     earliest_start: int
#     latest_start: int


# class DailyScheduleRequest(SQLModel):
#     company_id: uuid.UUID
#     date: datetime
#     trips: List[TripCreate]


# class SolverConfig(SQLModel):
#     timeout_seconds: int = Field(default=300, ge=10, le=3600)
#     use_soft_constraints: bool = Field(default=False)
#     max_vehicles: Optional[int] = Field(default=None, ge=1)
#     soft_constraint_penalty: int = Field(default=1000, ge=1)


# class OptimizationRequest(SQLModel):
#     company_id: uuid.UUID
#     date: datetime
#     optimization_group_id: uuid.UUID
#     config: SolverConfig = Field(default_factory=SolverConfig)


# class ValidationResult(SQLModel):
#     is_valid: bool
#     errors: List[str] = Field(default_factory=list)
#     warnings: List[str] = Field(default_factory=list)


# class AssignmentResult(SQLModel):
#     vehicle_id: str
#     trip_sequence: List[str]
#     start_times: List[int]
#     end_times: List[int]
#     is_last: List[bool]


# class OptimizationResult(SQLModel):
#     job_id: uuid.UUID
#     status: JobStatus
#     objective: Optional[float] = None
#     metrics: Dict[str, Any] = Field(default_factory=dict)
#     assignments: List[AssignmentResult] = Field(default_factory=list)
#     diagnostics: List[str] = Field(default_factory=list)


# class JobStatusResponse(SQLModel):
#     job_id: uuid.UUID
#     status: JobStatus
#     progress: float = Field(default=0.0, ge=0.0, le=1.0)
#     message: Optional[str] = None


# class OptimizationJobPublic(SQLModel):
#     id: uuid.UUID
#     status: JobStatus
#     objective: Optional[float]
#     created_at: datetime
#     updated_at: datetime
#     metrics: Dict[str, Any]
#     optimization_group_name: str


# class OptimizationJobsPublic(SQLModel):
#     data: List[OptimizationJobPublic]
#     count: int


# class DashboardStats(SQLModel):
#     ongoing_trips: int
#     distributed_vehicles: int
#     todays_trips: List[Dict[str, Any]]
#     kilometers_saved: float
#     fuel_savings: float


# # Generic message
# class Message(SQLModel):
#     message: str
