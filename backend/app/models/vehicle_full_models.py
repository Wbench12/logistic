# from enum import Enum
# from typing import List, Optional, Any
# from sqlmodel import Field, Relationship, SQLModel
# import uuid
# from .company_modelsold import Company

# # Vehicle and Maintenance Models

# class VehicleStatus(str, Enum):
#     AVAILABLE = "disponible"
#     ON_MISSION = "en_mission"
#     MAINTENANCE = "maintenance"

# class VehicleState(str, Enum):
#     ACTIVE = "actif"
#     INACTIVE = "inactif"

# class VehicleCategory(SQLModel, table=True):
#     id: str = Field(primary_key=True, max_length=10)
#     name: str = Field(max_length=100)
#     sector: str
#     description: Optional[str] = Field(default=None)
#     main_use: Optional[str] = Field(default=None)
#     technical_constraints: Optional[str] = Field(default=None)
#     capacity_range: Optional[str] = Field(default=None)
#     temperature_control: Optional[bool] = Field(default=False)
#     temperature_range: Optional[str] = Field(default=None)
#     requires_adr_certification: bool = Field(default=False)
#     requires_special_equipment: bool = Field(default=False)
#     vehicles: List["Vehicle"] = Relationship(back_populates="category")
#     optimization_groups: List[Any] = Relationship(back_populates="vehicle_category")

# class Vehicle(SQLModel, table=True):
#     id: str = Field(primary_key=True, max_length=50)
#     company_id: uuid.UUID = Field(foreign_key="company.id")
#     category_id: str = Field(foreign_key="vehiclecategory.id")
#     depot_location: Optional[str] = Field(description="Depot location address or coordinates")
#     capacity: float = Field(description="Capacity in tons or m³")
#     current_status: VehicleStatus = Field(default=VehicleStatus.AVAILABLE)
#     state: VehicleState = Field(default=VehicleState.ACTIVE)
#     current_kilometers: float = Field(default=0.0)
#     last_technical_control: Optional[Any] = Field(default=None)
#     last_insurance_check: Optional[Any] = Field(default=None)
#     year: Optional[int] = Field(default=None)
#     brand: Optional[str] = Field(default=None)
#     model: Optional[str] = Field(default=None)
#     fuel_type: Optional[str] = Field(default=None)
#     created_at: Any = Field(default_factory=lambda: None)
#     company: Company = Relationship(back_populates="vehicles")
#     category: VehicleCategory = Relationship(back_populates="vehicles")
#     assignments: List[Any] = Relationship(back_populates="vehicle")
#     maintenance_records: List[Any] = Relationship(back_populates="vehicle")
#     documents: List[Any] = Relationship(back_populates="vehicle")

# class VehicleCreate(SQLModel):
#     id: str
#     category_id: str
#     depot_location: str
#     capacity: float
#     year: Optional[int] = None
#     brand: Optional[str] = None
#     model: Optional[str] = None
#     fuel_type: Optional[str] = None

# class MaintenanceRecord(SQLModel, table=True):
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     vehicle_id: str = Field(foreign_key="vehicle.id")
#     maintenance_type: str
#     description: str
#     cost: Optional[float] = Field(default=None)
#     kilometers: float
#     maintenance_date: Any
#     next_maintenance_date: Optional[Any] = Field(default=None)
#     next_maintenance_kilometers: Optional[float] = Field(default=None)
#     created_at: Any = Field(default_factory=lambda: None)
#     vehicle: Vehicle = Relationship(back_populates="maintenance_records")

# class VehicleDocument(SQLModel, table=True):
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     vehicle_id: str = Field(foreign_key="vehicle.id")
#     document_type: str
#     file_url: str
#     file_name: str
#     upload_date: Any = Field(default_factory=lambda: None)
#     expiry_date: Optional[Any] = Field(default=None)
#     vehicle: Vehicle = Relationship(back_populates="documents")
