
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from sqlmodel import Field, Relationship, SQLModel
import uuid
from .user_models import User
from .company_models import Company

# --- Core Optimization Data Models (aligned with solver.py) ---
class Trip(SQLModel, table=True):
    id: str = Field(primary_key=True, max_length=50)
    company_id: str = Field(index=True)
    orig: Any
    dest: Any
    earliest: int
    latest: int
    duration: int
    service: int = 0
    demand: int = 1
    r_i0: float = 0.0
    # Relationships
    company: Optional["Company"] = Relationship(back_populates="trips")

class Vehicle(SQLModel, table=True):
    id: str = Field(primary_key=True, max_length=50)
    type_id: Optional[str] = None
    capacity: int
    depot: Any = None
    available_from: int = 0
    available_to: int = 24 * 60

class Config(SQLModel):
    timeout_seconds: float = 300.0
    num_workers: int = 4
    default_travel_time: int = 15
    default_return_distance: float = 20.0
    conservative_percentile: float = 0.9

# Optimization, Assignment, and Result Models

class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    INFEASIBLE = "INFEASIBLE"
    FAILED = "FAILED"

class OptimizationGroup(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100)
    sector: str
    vehicle_category_id: str = Field(foreign_key="vehiclecategory.id")
    description: Optional[str] = Field(default=None)
    created_at: Any = Field(default_factory=lambda: None)
    vehicle_category: Optional[Any] = Relationship(back_populates="optimization_groups")
    optimization_jobs: List["OptimizationJob"] = Relationship(back_populates="optimization_group")

class OptimizationJob(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="user.id")
    company_id: uuid.UUID = Field(foreign_key="company.id")
    optimization_group_id: uuid.UUID = Field(foreign_key="optimizationgroup.id")
    status: JobStatus = Field(default=JobStatus.PENDING)
    objective: Optional[float] = Field(default=None)
    config: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    diagnostics: List[str] = Field(default_factory=list)
    created_at: Any = Field(default_factory=lambda: None)
    updated_at: Any = Field(default_factory=lambda: None)
    owner: User = Relationship(back_populates="optimization_jobs")
    company: Company = Relationship(back_populates="optimization_jobs")
    optimization_group: OptimizationGroup = Relationship(back_populates="optimization_jobs")
    assignments: List["Assignment"] = Relationship(back_populates="job")

class Assignment(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_id: uuid.UUID = Field(foreign_key="optimizationjob.id")
    vehicle_id: str = Field(foreign_key="vehicle.id")
    trip_id: uuid.UUID = Field(foreign_key="trip.id")
    sequence_order: int = Field(description="Order in vehicle's route")
    start_time: int = Field(description="Actual start time for this trip (minutes from midnight)")
    end_time: int = Field(description="Actual end time for this trip (minutes from midnight)")
    is_last: bool = Field(description="Whether this is the last trip for the vehicle")
    job: OptimizationJob = Relationship(back_populates="assignments")
    vehicle: Any = Relationship(back_populates="assignments")
    trip: Any = Relationship(back_populates="assignments")


class AssignmentResult(SQLModel):
    vehicle_id: str
    trip_sequence: List[str]
    start_times: List[int]
    end_times: List[int]
    is_last: List[bool]


class OptimizationResult(SQLModel):
    job_id: str
    status: str
    objective: Optional[float] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    assignments: List[AssignmentResult] = Field(default_factory=list)
    diagnostics: List[str] = Field(default_factory=list)
