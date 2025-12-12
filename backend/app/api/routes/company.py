"""
API Routes for Company and Vehicle Management

Request Lifecycle Example for POST /companies/:
1. Request hits FastAPI router
2. Dependency injection: SessionDep provides DB session, CurrentUser provides authenticated user
3. Business logic layer: crud.create_company() handles database operations
4. Response serialization: Returns CompanyPublic model
5. Database transaction committed, response sent to client
"""
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import Message
from app.models.company_models import (
    Company,
    CompanyCreate,
    CompanyPublic,
    CompanyUpdate,
    Vehicle,
    VehicleCreate,
    VehiclePublic,
    VehiclesPublic,
    VehicleUpdate,
)

# ============= COMPANY ROUTES =============
router_companies = APIRouter(prefix="/companies", tags=["companies"])

@router_companies.post("/", response_model=CompanyPublic)
def create_company(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    company_in: CompanyCreate
) -> Any:
    """
    Create company profile for current user.
    
    Lifecycle:
    1. Validate user doesn't already have a company
    2. Check NIS/NIF uniqueness
    3. Create company record linked to user
    4. Return created company
    """
    # Check if user already has a company
    existing_company = crud.get_company_by_user(session=session, user_id=current_user.id)
    if existing_company:
        raise HTTPException(
            status_code=400,
            detail="User already has a company profile"
        )
    
    # Check NIS uniqueness
    existing_nis = crud.get_company_by_nis(session=session, nis=company_in.nis)
    if existing_nis:
        raise HTTPException(
            status_code=400,
            detail="Company with this NIS already exists"
        )
    
    company = crud.create_company(
        session=session,
        company_create=company_in,
        user_id=current_user.id
    )
    return company

@router_companies.get("/me", response_model=CompanyPublic)
def read_company_me(
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Get current user's company profile.
    """
    company = crud.get_company_by_user(session=session, user_id=current_user.id)
    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company profile not found"
        )
    return company

@router_companies.patch("/me", response_model=CompanyPublic)
def update_company_me(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    company_in: CompanyUpdate
) -> Any:
    """
    Update current user's company profile.
    """
    company = crud.get_company_by_user(session=session, user_id=current_user.id)
    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company profile not found"
        )
    
    company = crud.update_company(
        session=session,
        db_company=company,
        company_update=company_in
    )
    return company

@router_companies.get("/{company_id}", response_model=CompanyPublic)
def read_company(
    company_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Get company by ID (admin only or own company).
    """
    company = session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check permissions
    if not current_user.is_superuser and company.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return company

# ============= VEHICLE ROUTES =============
router_vehicles = APIRouter(prefix="/vehicles", tags=["vehicles"])

@router_vehicles.get("/", response_model=VehiclesPublic)
def read_vehicles(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """
    Retrieve vehicles for current user's company.
    
    Lifecycle:
    1. Get user's company
    2. Fetch vehicles with pagination
    3. Return vehicles list with count
    """
    company = crud.get_company_by_user(session=session, user_id=current_user.id)
    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company profile not found. Create one first."
        )
    
    vehicles, count = crud.get_vehicles_by_company(
        session=session,
        company_id=company.id,
        skip=skip,
        limit=limit
    )
    
    return VehiclesPublic(data=vehicles, count=count)

@router_vehicles.post("/", response_model=VehiclePublic)
def create_vehicle(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    vehicle_in: VehicleCreate
) -> Any:
    """
    Create new vehicle.
    
    Lifecycle:
    1. Verify company ownership
    2. Validate vehicle data
    3. Create vehicle record
    4. Return created vehicle
    """
    company = crud.get_company_by_user(session=session, user_id=current_user.id)
    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company profile not found"
        )
    
    # Verify company_id matches
    if vehicle_in.company_id != company.id:
        raise HTTPException(
            status_code=403,
            detail="Cannot create vehicle for another company"
        )
    
    vehicle = crud.create_vehicle(session=session, vehicle_create=vehicle_in)
    return vehicle

@router_vehicles.get("/{vehicle_id}", response_model=VehiclePublic)
def read_vehicle(
    vehicle_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Get vehicle by ID.
    """
    vehicle = crud.get_vehicle(session=session, vehicle_id=vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    # Check ownership
    company = crud.get_company_by_user(session=session, user_id=current_user.id)
    if not company or vehicle.company_id != company.id:
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return vehicle

@router_vehicles.put("/{vehicle_id}", response_model=VehiclePublic)
def update_vehicle(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    vehicle_id: uuid.UUID,
    vehicle_in: VehicleUpdate
) -> Any:
    """
    Update vehicle.
    """
    vehicle = crud.get_vehicle(session=session, vehicle_id=vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    # Check ownership
    company = crud.get_company_by_user(session=session, user_id=current_user.id)
    if not company or vehicle.company_id != company.id:
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    
    vehicle = crud.update_vehicle(
        session=session,
        db_vehicle=vehicle,
        vehicle_update=vehicle_in
    )
    return vehicle

@router_vehicles.delete("/{vehicle_id}")
def delete_vehicle(
    session: SessionDep,
    current_user: CurrentUser,
    vehicle_id: uuid.UUID
) -> Message:
    """
    Delete vehicle.
    """
    vehicle = crud.get_vehicle(session=session, vehicle_id=vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    # Check ownership
    company = crud.get_company_by_user(session=session, user_id=current_user.id)
    if not company or vehicle.company_id != company.id:
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    
    crud.delete_vehicle(session=session, vehicle_id=vehicle_id)
    return Message(message="Vehicle deleted successfully")