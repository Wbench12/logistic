from collections.abc import Generator
from typing import Annotated, Optional
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session, select

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import TokenPayload, User
from app.models.company_models import Company, Vehicle
from app.models.trip_models import Trip, MapMarker

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


# ============= COMPANY DEPENDENCIES =============

def get_current_user_company(session: SessionDep, current_user: CurrentUser) -> Company:
    """
    Get the company associated with the current user.
    
    Assumes one user belongs to one company (simplified model).
    In production, you might need to handle multiple companies per user.
    """
    statement = select(Company).where(Company.user_id == current_user.id)
    company = session.exec(statement).first()
    
    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company profile not found. Please complete company registration."
        )
    
    if not company.is_active:
        raise HTTPException(
            status_code=403,
            detail="Company account is inactive"
        )
    
    return company


CurrentCompany = Annotated[Company, Depends(get_current_user_company)]


def get_company_resource_access(
    session: SessionDep,
    current_user: CurrentUser,
    resource_company_id: Optional[UUID] = None,
    resource_id: Optional[UUID] = None,
    resource_type: str = "trip"
) -> Company:
    """
    Universal dependency for checking company resource access.
    
    Usage:
    - For trips: resource_company_id = trip.company_id
    - For vehicles: resource_company_id = vehicle.company_id
    - For markers: resource_company_id = marker.company_id
    """
    # Superusers can access any resource
    if current_user.is_superuser:
        # Return the resource's company or a placeholder
        if resource_company_id:
            company = session.get(Company, resource_company_id)
            if company:
                return company
    
    # Get user's company
    user_company = get_current_user_company(session, current_user)
    
    # Check if user has access to this specific resource
    if resource_company_id and resource_company_id != user_company.id:
        raise HTTPException(
            status_code=403,
            detail=f"You don't have permission to access this {resource_type}"
        )
    
    # Additional resource-specific checks
    if resource_id:
        if resource_type == "trip":
            trip = session.get(Trip, resource_id)
            if trip and trip.company_id != user_company.id:
                raise HTTPException(
                    status_code=403,
                    detail="You don't have permission to access this trip"
                )
        elif resource_type == "vehicle":
            vehicle = session.get(Vehicle, resource_id)
            if vehicle and vehicle.company_id != user_company.id:
                raise HTTPException(
                    status_code=403,
                    detail="You don't have permission to access this vehicle"
                )
        elif resource_type == "marker":
            marker = session.get(MapMarker, resource_id)
            if marker and marker.company_id != user_company.id:
                raise HTTPException(
                    status_code=403,
                    detail="You don't have permission to access this marker"
                )
    
    return user_company


CompanyResourceAccess = Annotated[Company, Depends(get_company_resource_access)]


def verify_company_vehicle(
    session: SessionDep,
    current_company: CurrentCompany,
    vehicle_id: UUID
) -> Vehicle:
    """
    Verify that a vehicle belongs to the current company.
    """
    vehicle = session.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    if vehicle.company_id != current_company.id:
        raise HTTPException(
            status_code=403,
            detail="Vehicle does not belong to your company"
        )
    
    return vehicle


CompanyVehicle = Annotated[Vehicle, Depends(verify_company_vehicle)]


def verify_company_trip(
    session: SessionDep,
    current_company: CurrentCompany,
    trip_id: UUID
) -> Trip:
    """
    Verify that a trip belongs to the current company.
    """
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.company_id != current_company.id:
        raise HTTPException(
            status_code=403,
            detail="Trip does not belong to your company"
        )
    
    return trip


CompanyTrip = Annotated[Trip, Depends(verify_company_trip)]


def verify_company_marker(
    session: SessionDep,
    current_company: CurrentCompany,
    marker_id: UUID
) -> MapMarker:
    """
    Verify that a map marker belongs to the current company.
    """
    marker = session.get(MapMarker, marker_id)
    if not marker:
        raise HTTPException(status_code=404, detail="Map marker not found")
    
    if marker.company_id != current_company.id:
        raise HTTPException(
            status_code=403,
            detail="Map marker does not belong to your company"
        )
    
    return marker


CompanyMarker = Annotated[MapMarker, Depends(verify_company_marker)]


def get_company_from_query(
    session: SessionDep,
    current_user: CurrentUser,
    company_id: Optional[UUID] = None
) -> Company:
    """
    Get company from query parameter, with access control.
    For admin endpoints that accept company_id parameter.
    """
    if company_id:
        # Admin can access any company, regular users only their own
        if current_user.is_superuser:
            company = session.get(Company, company_id)
            if not company:
                raise HTTPException(status_code=404, detail="Company not found")
            return company
        else:
            # Non-admin users can only specify their own company
            user_company = get_current_user_company(session, current_user)
            if company_id != user_company.id:
                raise HTTPException(
                    status_code=403,
                    detail="You can only access your own company"
                )
            return user_company
    else:
        # No company_id specified, use current user's company
        return get_current_user_company(session, current_user)


CompanyFromQuery = Annotated[Company, Depends(get_company_from_query)]