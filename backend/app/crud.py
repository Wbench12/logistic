from datetime import datetime
from typing import Any, Optional
import uuid

from sqlmodel import Session, select, and_

from app.core.security import get_password_hash, verify_password
from app.models.company_models import (
    Company,
    CompanyCreate,
    CompanyUpdate,
    Vehicle,
    VehicleCategory,
    VehicleCreate,
    VehicleStatus,
    VehicleUpdate,
)
from app.models.trip_models import (
    OptimizationBatch,
    Trip,
    TripCreate,
    TripStatus,
    TripUpdate,
)
from app.models.user_models import User, UserCreate, UserUpdate


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user

# ============= COMPANY CRUD =============
def create_company(*, session: Session, company_create: CompanyCreate, user_id: uuid.UUID) -> Company:
    """Create a new company linked to a user"""
    db_company = Company.model_validate(
        company_create,
        update={"user_id": user_id}
    )
    session.add(db_company)
    session.commit()
    session.refresh(db_company)
    return db_company

def get_company_by_user(*, session: Session, user_id: uuid.UUID) -> Optional[Company]:
    """Get company by user ID"""
    statement = select(Company).where(Company.user_id == user_id)
    return session.exec(statement).first()

def get_company_by_nis(*, session: Session, nis: str) -> Optional[Company]:
    """Get company by NIS"""
    statement = select(Company).where(Company.nis == nis)
    return session.exec(statement).first()

def update_company(
    *, 
    session: Session, 
    db_company: Company, 
    company_update: CompanyUpdate
) -> Company:
    """Update company details"""
    company_data = company_update.model_dump(exclude_unset=True)
    db_company.sqlmodel_update(company_data)
    db_company.updated_at = datetime.utcnow()
    session.add(db_company)
    session.commit()
    session.refresh(db_company)
    return db_company

# ============= VEHICLE CRUD =============
def create_vehicle(*, session: Session, vehicle_create: VehicleCreate) -> Vehicle:
    """Create a new vehicle"""
    db_vehicle = Vehicle.model_validate(vehicle_create)
    session.add(db_vehicle)
    session.commit()
    session.refresh(db_vehicle)
    return db_vehicle

def get_vehicles_by_company(
    *, 
    session: Session, 
    company_id: uuid.UUID, 
    skip: int = 0, 
    limit: int = 100
) -> tuple[list[Vehicle], int]:
    """Get all vehicles for a company with pagination"""
    statement = select(Vehicle).where(Vehicle.company_id == company_id).offset(skip).limit(limit)
    vehicles = session.exec(statement).all()
    
    count_statement = select(Vehicle).where(Vehicle.company_id == company_id)
    count = len(session.exec(count_statement).all())
    
    return list(vehicles), count

def get_vehicle(*, session: Session, vehicle_id: uuid.UUID) -> Optional[Vehicle]:
    """Get vehicle by ID"""
    return session.get(Vehicle, vehicle_id)

def update_vehicle(
    *, 
    session: Session, 
    db_vehicle: Vehicle, 
    vehicle_update: VehicleUpdate
) -> Vehicle:
    """Update vehicle details"""
    vehicle_data = vehicle_update.model_dump(exclude_unset=True)
    db_vehicle.sqlmodel_update(vehicle_data)
    db_vehicle.updated_at = datetime.utcnow()
    session.add(db_vehicle)
    session.commit()
    session.refresh(db_vehicle)
    return db_vehicle

def delete_vehicle(*, session: Session, vehicle_id: uuid.UUID) -> None:
    """Delete a vehicle"""
    vehicle = session.get(Vehicle, vehicle_id)
    if vehicle:
        session.delete(vehicle)
        session.commit()

def get_available_vehicles_by_category(
    *,
    session: Session,
    category: VehicleCategory | str,
    date: datetime
) -> list[Vehicle]:
    """Get available vehicles of a specific category for optimization"""
    if isinstance(category, VehicleCategory):
        category_value = category
    else:
        try:
            category_value = VehicleCategory(category)
        except ValueError as exc:  # pragma: no cover - defensive branch
            raise ValueError(f"Unknown vehicle category: {category}") from exc

    statement = select(Vehicle).where(
        and_(
            Vehicle.category == category_value,
            Vehicle.status == VehicleStatus.AVAILABLE,
            Vehicle.is_active==(True),
            Vehicle.updated_at <= date,
        )
    )
    return list(session.exec(statement).all())

# ============= TRIP CRUD =============
def create_trip(
    *, 
    session: Session, 
    trip_create: TripCreate, 
    company_id: uuid.UUID
) -> Trip:
    """Create a new trip"""
    db_trip = Trip.model_validate(
        trip_create,
        update={"company_id": company_id}
    )
    session.add(db_trip)
    session.commit()
    session.refresh(db_trip)
    return db_trip

def get_trips_by_company(
    *, 
    session: Session, 
    company_id: uuid.UUID, 
    skip: int = 0, 
    limit: int = 100,
    status: Optional[TripStatus] = None
) -> tuple[list[Trip], int]:
    """Get all trips for a company with optional status filter"""
    base_query = select(Trip).where(Trip.company_id == company_id)
    
    if status:
        base_query = base_query.where(Trip.status == status)
    
    statement = base_query.offset(skip).limit(limit)
    trips = session.exec(statement).all()
    
    count_statement = base_query
    count = len(session.exec(count_statement).all())
    
    return list(trips), count

def get_trip(*, session: Session, trip_id: uuid.UUID) -> Optional[Trip]:
    """Get trip by ID"""
    return session.get(Trip, trip_id)

def update_trip(
    *, 
    session: Session, 
    db_trip: Trip, 
    trip_update: TripUpdate
) -> Trip:
    """Update trip details"""
    trip_data = trip_update.model_dump(exclude_unset=True)
    db_trip.sqlmodel_update(trip_data)
    db_trip.updated_at = datetime.utcnow()
    session.add(db_trip)
    session.commit()
    session.refresh(db_trip)
    return db_trip

def delete_trip(*, session: Session, trip_id: uuid.UUID) -> None:
    """Delete a trip"""
    trip = session.get(Trip, trip_id)
    if trip:
        session.delete(trip)
        session.commit()

def get_trips_for_date(
    *, 
    session: Session, 
    target_date: datetime
) -> list[Trip]:
    """Get all planned trips for a specific date (for optimization)"""
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    statement = select(Trip).where(
        and_(
            Trip.departure_datetime >= start_of_day,
            Trip.departure_datetime <= end_of_day,
            Trip.status == TripStatus.PLANNED
        )
    )
    return list(session.exec(statement).all())

def get_trips_by_batch(
    *, 
    session: Session, 
    batch_id: uuid.UUID
) -> list[Trip]:
    """Get all trips that were part of an optimization batch"""
    statement = select(Trip).where(Trip.optimization_batch_id == batch_id)
    return list(session.exec(statement).all())

# ============= OPTIMIZATION BATCH CRUD =============
def create_optimization_batch(
    *, 
    session: Session, 
    batch_date: datetime
) -> OptimizationBatch:
    """Create a new optimization batch"""
    db_batch = OptimizationBatch(batch_date=batch_date)
    session.add(db_batch)
    session.commit()
    session.refresh(db_batch)
    return db_batch

def update_optimization_batch(
    *, 
    session: Session, 
    batch_id: uuid.UUID, 
    **kwargs
) -> Optional[OptimizationBatch]:
    """Update optimization batch with results"""
    batch = session.get(OptimizationBatch, batch_id)
    if batch:
        for key, value in kwargs.items():
            setattr(batch, key, value)
        session.add(batch)
        session.commit()
        session.refresh(batch)
    return batch

def get_optimization_batch(
    *, 
    session: Session, 
    batch_id: uuid.UUID
) -> Optional[OptimizationBatch]:
    """Get optimization batch by ID"""
    return session.get(OptimizationBatch, batch_id)
