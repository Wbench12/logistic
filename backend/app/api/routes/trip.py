"""
API Routes for Trip Management and Optimization

Request Lifecycle for Optimization:
1. POST /trips/optimize/{date} -> trigger optimization
2. Fetch all trips for date (Business Logic Layer)
3. Group trips by vehicle compatibility
4. Run CP-SAT solver for each group (Solver Service Layer)
5. Update database with assignments (Data Layer)
6. Return metrics to client
"""
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import Message
from app.models.trip_models import (
    DashboardMetrics,
    OptimizationBatch,
    OptimizationBatchPublic,
    Trip,
    TripCreate,
    TripPublic,
    TripStatus,
    TripUpdate,
    TripsPublic,
)
from app.services.optimization import optimize_trips_for_date

# ============= TRIP ROUTES =============
router_trips = APIRouter(prefix="/trips", tags=["trips"])

# Specific routes first (before dynamic {id} routes)
@router_trips.get("/today", response_model=TripsPublic)
def read_today_trips(
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Get trips scheduled for today for current user's company.
    """
    company = crud.get_company_by_user(session=session, user_id=current_user.id)
    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company profile not found"
        )
    
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    all_trips = crud.get_trips_for_date(session=session, target_date=today)
    # Filter for current company
    company_trips = [t for t in all_trips if t.company_id == company.id]
    
    trip_data = [TripPublic.model_validate(trip) for trip in company_trips]
    return TripsPublic(data=trip_data, count=len(company_trips))

# Optimization routes before ID routes
@router_trips.post("/optimize/{date}", response_model=dict)
def optimize_trips(
    date: str,  # Format: YYYY-MM-DD
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Trigger optimization for a specific date.
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can trigger optimization"
        )
    
    result = optimize_trips_for_date(
        session=session,
        target_date=target_date
    )
    
    return result

@router_trips.get("/optimization/batches", response_model=list[OptimizationBatchPublic])
def read_optimization_batches(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 20
) -> Any:
    """
    Get list of optimization batches (history).
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can view optimization history"
        )
    
    statement = select(OptimizationBatch).order_by(
        OptimizationBatch.created_at.desc()
    ).offset(skip).limit(limit)
    
    batches = session.exec(statement).all()
    return [OptimizationBatchPublic.model_validate(batch) for batch in batches]

@router_trips.get("/optimization/batch/{batch_id}", response_model=dict)
def read_optimization_batch_details(
    batch_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Get detailed results of an optimization batch.
    """
    batch = crud.get_optimization_batch(session=session, batch_id=batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Optimization batch not found")
    
    trips = crud.get_trips_by_batch(session=session, batch_id=batch_id)
    
    company_assignments: dict[uuid.UUID, list[dict[str, Any]]] = {}
    for trip in trips:
        if trip.company_id not in company_assignments:
            company_assignments[trip.company_id] = []
        company_assignments[trip.company_id].append({
            'trip_id': str(trip.id),
            'vehicle_id': str(trip.assigned_vehicle_id) if trip.assigned_vehicle_id else None,
            'is_last_in_chain': trip.is_last_in_chain
        })
    
    return {
        'batch': batch,
        'trips_count': len(trips),
        'company_assignments': company_assignments
    }

# Generic routes (after specific ones)
@router_trips.get("/", response_model=TripsPublic)
def read_trips(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    status: Optional[TripStatus] = None
) -> Any:
    """
    Retrieve trips for current user's company.
    
    Query Parameters:
    - skip: Pagination offset
    - limit: Number of results
    - status: Filter by trip status (planned, in_progress, completed, cancelled)
    
    Lifecycle:
    1. Get user's company
    2. Fetch trips with filters
    3. Return paginated list
    """
    company = crud.get_company_by_user(session=session, user_id=current_user.id)
    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company profile not found"
        )
    
    trips, count = crud.get_trips_by_company(
        session=session,
        company_id=company.id,
        skip=skip,
        limit=limit,
        status=status
    )
    trip_data = [TripPublic.model_validate(trip) for trip in trips]

    return TripsPublic(data=trip_data, count=count)

@router_trips.post("/", response_model=TripPublic)
def create_trip(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    trip_in: TripCreate
) -> Any:
    """
    Create new trip.
    
    Lifecycle:
    1. Verify company ownership
    2. Verify vehicle belongs to company
    3. Validate trip data (dates, capacity, etc.)
    4. Create trip record
    5. Calculate distance/duration if coordinates provided
    """
    company = crud.get_company_by_user(session=session, user_id=current_user.id)
    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company profile not found"
        )
    
    # Verify vehicle ownership
    vehicle = crud.get_vehicle(session=session, vehicle_id=trip_in.vehicle_id)
    if not vehicle or vehicle.company_id != company.id:
        raise HTTPException(
            status_code=403,
            detail="Vehicle not found or does not belong to your company"
        )
    
    # Validate dates
    if trip_in.departure_datetime >= trip_in.arrival_datetime_planned:
        raise HTTPException(
            status_code=400,
            detail="Arrival time must be after departure time"
        )
    
    # Create trip
    trip = crud.create_trip(
        session=session,
        trip_create=trip_in,
        company_id=company.id
    )
    
    # Calculate distance if coordinates provided
    if all([trip.departure_lat, trip.departure_lng, trip.arrival_lat, trip.arrival_lng]):
        from app.services.optimization import calculate_trip_distance
        trip.distance_km = calculate_trip_distance(trip)
        session.add(trip)
        session.commit()
        session.refresh(trip)
    
    return trip

@router_trips.get("/{trip_id}", response_model=TripPublic)
def read_trip(
    trip_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Get trip by ID.
    """
    trip = crud.get_trip(session=session, trip_id=trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Check ownership
    company = crud.get_company_by_user(session=session, user_id=current_user.id)
    if not company or trip.company_id != company.id:
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return trip

@router_trips.put("/{trip_id}", response_model=TripPublic)
def update_trip(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    trip_id: uuid.UUID,
    trip_in: TripUpdate
) -> Any:
    """
    Update trip.
    """
    trip = crud.get_trip(session=session, trip_id=trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Check ownership
    company = crud.get_company_by_user(session=session, user_id=current_user.id)
    if not company or trip.company_id != company.id:
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    
    trip = crud.update_trip(
        session=session,
        db_trip=trip,
        trip_update=trip_in
    )
    return trip

@router_trips.delete("/{trip_id}")
def delete_trip(
    session: SessionDep,
    current_user: CurrentUser,
    trip_id: uuid.UUID
) -> Message:
    """
    Delete trip.
    """
    trip = crud.get_trip(session=session, trip_id=trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Check ownership
    company = crud.get_company_by_user(session=session, user_id=current_user.id)
    if not company or trip.company_id != company.id:
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    
    crud.delete_trip(session=session, trip_id=trip_id)
    return Message(message="Trip deleted successfully")

# ============= DASHBOARD ROUTES =============
router_dashboard = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router_dashboard.get("/", response_model=DashboardMetrics)
def read_dashboard(
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Get dashboard metrics for current user's company.
    
    Returns KPIs:
    - Trips in progress
    - Vehicles distributed (active today)
    - Km reduced today
    - Fuel saved today
    - Daily trips list
    - ESG contribution (CO2 saved)
    """
    company = crud.get_company_by_user(session=session, user_id=current_user.id)
    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company profile not found"
        )
    
    # Get today's trips
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    all_today_trips = crud.get_trips_for_date(session=session, target_date=today)
    
    # Filter for company
    company_trips = [t for t in all_today_trips if t.company_id == company.id]
    
    # Calculate metrics
    trips_in_progress = len([t for t in company_trips if t.status == TripStatus.IN_PROGRESS])
    
    # Vehicles used today
    vehicle_ids = set(t.vehicle_id for t in company_trips)
    vehicles_distributed = len(vehicle_ids)
    
    # KM and fuel saved (from optimization batch if available)
    km_reduced = 0.0
    fuel_saved = 0.0
    
    # Get latest optimization batch for today
    batch_statement = select(OptimizationBatch).where(
        OptimizationBatch.batch_date == today
    ).order_by(OptimizationBatch.created_at.desc())
    latest_batch = session.exec(batch_statement).first()
    
    if latest_batch:
        km_reduced = latest_batch.km_saved or 0.0
        fuel_saved = latest_batch.fuel_saved_liters or 0.0
    
    # ESG contribution (CO2 saved)
    # Average: 2.3 kg CO2 per liter of diesel
    co2_saved_kg = fuel_saved * 2.3
    
    return DashboardMetrics(
        trips_in_progress=trips_in_progress,
        vehicles_distributed=vehicles_distributed,
        km_reduced_today=km_reduced,
        fuel_saved_today=fuel_saved,
        daily_trips=[TripPublic.model_validate(trip) for trip in company_trips],
        esg_contribution={
            'co2_saved_kg': co2_saved_kg,
            'trees_equivalent': int(co2_saved_kg / 21),  # 1 tree absorbs ~21kg CO2/year
            'fuel_saved_liters': fuel_saved
        }
    )