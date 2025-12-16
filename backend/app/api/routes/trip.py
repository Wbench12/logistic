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
from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict, cast

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Query
from sqlmodel import select, func, Session
from sqlalchemy import desc

from app import crud
from app.api.deps import (
    CurrentUser, 
    SessionDep, 
    CurrentCompany,
    CompanyVehicle,
    CompanyTrip,
    CompanyMarker,
    get_current_active_superuser
)
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
    MapMarker,
    CompanyOptimizationResult
)
from app.models.company_models import Vehicle, VehicleCategory
from app.services.valhalla_service import ValhallaService
from app.services.trip_upload_service import TripUploadService
import logging
logger = logging.getLogger(__name__)

# ============= TRIP ROUTES =============
router_trips = APIRouter(prefix="/trips", tags=["trips"])

# Specific routes first (before dynamic {id} routes)
@router_trips.get("/today", response_model=TripsPublic)
def read_today_trips(
    session: SessionDep,
    current_company: CurrentCompany
) -> Any:
    """
    Get trips scheduled for today for current user's company.
    """
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    company_trips = crud.get_trips_for_date_and_company(
        session=session, 
        target_date=today,
        company_id=current_company.id
    )
    
    trip_data = [TripPublic.model_validate(trip) for trip in company_trips]
    return TripsPublic(data=trip_data, count=len(company_trips))

@router_trips.get("/date/{date}", response_model=TripsPublic)
def read_trips_by_date(
    date: str,
    session: SessionDep,
    current_company: CurrentCompany,
    status: Optional[TripStatus] = None,
    include_optimized: bool = True
) -> Any:
    """
    Get trips for a specific date.
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    company_trips = crud.get_trips_for_date_and_company(
        session=session,
        target_date=target_date,
        company_id=current_company.id,
        status=status,
        include_optimized=include_optimized
    )
    
    trip_data = [TripPublic.model_validate(trip) for trip in company_trips]
    return TripsPublic(data=trip_data, count=len(company_trips))

# Optimization routes before ID routes
@router_trips.post("/optimize/{date}", response_model=dict)
def optimize_trips(
    date: str,
    session: SessionDep,
    current_user: CurrentUser,
    optimization_type: str = "cross_company",
    company_id: Optional[uuid.UUID] = None
) -> Any:
    """
    Trigger optimization for a specific date.
    
    Query Parameters:
    - optimization_type: "cross_company" or "single_company"
    - company_id: Optional, for single company optimization (admin can specify any)
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Check permissions
    if optimization_type == "cross_company":
        # Only admins can trigger cross-company optimization
        get_current_active_superuser(current_user)
    else:
        # Single company optimization
        if company_id and not current_user.is_superuser:
            # Regular users can only optimize their own company
            from app.api.deps import get_current_user_company
            user_company = get_current_user_company(session, current_user)
            if company_id != user_company.id:
                raise HTTPException(
                    status_code=403,
                    detail="You can only optimize your own company"
                )
        elif not company_id:
            # No company_id specified, use current user's company
            from app.api.deps import get_current_user_company
            company_id = get_current_user_company(session, current_user).id
    
    # Import here to avoid circular imports
    from app.services.optimization import optimize_trips_for_date
    
    result = optimize_trips_for_date(
        session=session,
        target_date=target_date,
        company_id=company_id,
        optimization_type=optimization_type
    )
    
    return {
        "message": f"Optimization triggered for {date}",
        "target_date": date,
        "optimization_type": optimization_type,
        "company_id": str(company_id) if company_id else "all",
        "details": result
    }

@router_trips.get("/optimization/batches", response_model=list[OptimizationBatchPublic])
def read_optimization_batches(
    session: SessionDep,
    current_user: CurrentUser,
    current_company: CurrentCompany,
    skip: int = 0,
    limit: int = 20,
    company_id: Optional[uuid.UUID] = None
) -> Any:
    """
    Get list of optimization batches (history).
    """
    # Build query based on user permissions
    if current_user.is_superuser and company_id:
        # Admin viewing specific company
        participating_companies_col = cast(Any, OptimizationBatch.participating_companies)
        query = select(OptimizationBatch).where(
            participating_companies_col.contains([str(company_id)])
        )
    elif current_user.is_superuser:
        # Admin viewing all batches
        query = select(OptimizationBatch)
    else:
        # Regular user can only see their company's batches
        participating_companies_col = cast(Any, OptimizationBatch.participating_companies)
        query = select(OptimizationBatch).where(
            participating_companies_col.contains([str(current_company.id)])
        )
    
    query = query.order_by(desc(cast(Any, OptimizationBatch.created_at))).offset(skip).limit(limit)
    
    batches = session.exec(query).all()
    return [OptimizationBatchPublic.model_validate(batch) for batch in batches]

@router_trips.get("/optimization/batch/{batch_id}", response_model=dict)
def read_optimization_batch_details(
    batch_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
    current_company: CurrentCompany
) -> Any:
    """
    Get detailed results of an optimization batch.
    """
    batch = crud.get_optimization_batch(session=session, batch_id=batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Optimization batch not found")
    
    # Check access: admin can see any batch, users only if their company participated
    if not current_user.is_superuser:
        if str(current_company.id) not in (batch.participating_companies or []):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view this batch"
            )
    
    trips = crud.get_trips_by_batch(session=session, batch_id=batch_id)
    
    company_assignments: dict[uuid.UUID, list[dict[str, Any]]] = {}
    for trip in trips:
        if trip.company_id not in company_assignments:
            company_assignments[trip.company_id] = []
        company_assignments[trip.company_id].append({
            'trip_id': str(trip.id),
            'vehicle_id': str(trip.assigned_vehicle_id) if trip.assigned_vehicle_id else None,
            'is_last_in_chain': trip.is_last_in_chain,
            'sequence_order': trip.sequence_order
        })
    
    return {
        'batch': OptimizationBatchPublic.model_validate(batch),
        'trips_count': len(trips),
        'company_assignments': company_assignments
    }

# Generic routes (after specific ones)
@router_trips.get("/", response_model=TripsPublic)
def read_trips(
    session: SessionDep,
    current_company: CurrentCompany,
    skip: int = 0,
    limit: int = 100,
    status: Optional[TripStatus] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Any:
    """
    Retrieve trips for current user's company.
    """
    # Parse date filters
    parsed_start = None
    parsed_end = None
    
    if start_date:
        try:
            parsed_start = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")
    
    if end_date:
        try:
            parsed_end = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")
    
    trips, count = crud.get_trips_by_company(
        session=session,
        company_id=current_company.id,
        skip=skip,
        limit=limit,
        status=status,
        start_date=parsed_start,
        end_date=parsed_end
    )
    
    trip_data = [TripPublic.model_validate(trip) for trip in trips]
    return TripsPublic(data=trip_data, count=count)

@router_trips.post("/", response_model=TripPublic)
def create_trip(
    *,
    session: SessionDep,
    current_company: CurrentCompany,
    trip_in: TripCreate
) -> Any:
    """
    Create new trip.
    """
    def infer_required_vehicle_category() -> VehicleCategory:
        cargo_val = trip_in.cargo_category.value if hasattr(trip_in.cargo_category, "value") else str(trip_in.cargo_category)
        cargo_val = cargo_val.lower()
        if cargo_val.startswith("a01"):
            return VehicleCategory.AG1
        if cargo_val.startswith("a02"):
            return VehicleCategory.AG2
        if cargo_val.startswith("a03"):
            return VehicleCategory.AG3
        if cargo_val.startswith("a04"):
            return VehicleCategory.AG4
        if cargo_val.startswith("b01"):
            return VehicleCategory.BT1
        if cargo_val.startswith("b02"):
            return VehicleCategory.BT4
        if cargo_val.startswith("b03"):
            return VehicleCategory.BT3
        if cargo_val.startswith("i01"):
            return VehicleCategory.IN2
        if cargo_val.startswith("i02"):
            return VehicleCategory.IN6
        if cargo_val.startswith("c01"):
            return VehicleCategory.CH2
        if cargo_val.startswith("c02"):
            return VehicleCategory.CH4
        return VehicleCategory.AG1

    # Verify vehicle belongs to company (only if provided)
    if trip_in.vehicle_id is not None:
        vehicle = session.get(Vehicle, trip_in.vehicle_id)
        if not vehicle or vehicle.company_id != current_company.id:
            raise HTTPException(
                status_code=403,
                detail="Vehicle not found or does not belong to your company"
            )

    # Ensure we store the required vehicle category even when no concrete vehicle is set
    if trip_in.required_vehicle_category is None:
        trip_in.required_vehicle_category = infer_required_vehicle_category()
    
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
        company_id=current_company.id
    )
    
    # Calculate route using Valhalla if coordinates provided
    if all([trip.departure_lat, trip.departure_lng, trip.arrival_lat, trip.arrival_lng]):
        from app.services.optimization import calculate_trip_distance_and_duration
        route_data = calculate_trip_distance_and_duration(trip)
        
        if route_data:
            trip.route_distance_km = route_data.get('distance_km')
            trip.route_duration_min = route_data.get('duration_min')
            trip.route_polyline = route_data.get('polyline')
            trip.route_calculated = True
            
            # Calculate return route if depot exists
            if current_company.depot_lat and current_company.depot_lng:
                return_data = calculate_trip_distance_and_duration(
                    trip,
                    start_lat=trip.arrival_lat,
                    start_lng=trip.arrival_lng,
                    end_lat=current_company.depot_lat,
                    end_lng=current_company.depot_lng
                )
                if return_data:
                    trip.return_distance_km = return_data.get('distance_km')
                    trip.return_duration_min = return_data.get('duration_min')
                    trip.return_route_polyline = return_data.get('polyline')
            
            session.add(trip)
            session.commit()
            session.refresh(trip)
    
    return trip

@router_trips.get("/{trip_id}", response_model=TripPublic)
def read_trip(
    trip: CompanyTrip,
    session: SessionDep
) -> Any:
    """
    Get trip by ID (automatically checks company access).
    """
    return trip

@router_trips.put("/{trip_id}", response_model=TripPublic)
def update_trip(
    *,
    session: SessionDep,
    trip: CompanyTrip,
    trip_in: TripUpdate
) -> Any:
    """
    Update trip.
    """
    # Additional validation for updates
    if trip_in.departure_datetime and trip_in.arrival_datetime_planned:
        if trip_in.departure_datetime >= trip_in.arrival_datetime_planned:
            raise HTTPException(
                status_code=400,
                detail="Arrival time must be after departure time"
            )
    
    trip = crud.update_trip(
        session=session,
        db_trip=trip,
        trip_update=trip_in
    )
    return trip

@router_trips.delete("/{trip_id}")
def delete_trip(
    session: SessionDep,
    trip: CompanyTrip
) -> Message:
    """
    Delete trip.
    """
    trip_id = trip.id
    
    crud.delete_trip(session=session, trip_id=trip_id)
    return Message(message="Trip deleted successfully")

# ============= UPLOAD ENDPOINTS =============
@router_trips.post("/upload", response_model=dict)
async def upload_trips(
    session: SessionDep,
    current_company: CurrentCompany,
    file: UploadFile = File(...),
    file_type: str = Form("csv"),
    validate_only: bool = Form(False)
) -> Any:
    """
    Upload trip planning file.
    
    Query Parameters:
    - validate_only: Only validate the file without saving
    """
    # Validate file type
    allowed_extensions = ['csv', 'xlsx', 'xls']
    file_extension = file.filename.split('.')[-1].lower() if file.filename else ''
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed: {allowed_extensions}"
        )
    
    # Save the uploaded file temporarily
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        valhalla_service = ValhallaService()
        upload_service = TripUploadService(valhalla_service)
        
        if validate_only:
            # Only validate
            result = await upload_service.validate_trip_file(tmp_path, file_extension)
        else:
            # Process and save
            result = await upload_service.process_upload_file(
                session=session,
                company_id=current_company.id,
                file_path=tmp_path,
                file_type=file_extension
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload processing failed: {str(e)}")
    finally:
        os.unlink(tmp_path)

@router_trips.get("/upload/history", response_model=List[Dict])
def get_upload_history(
    session: SessionDep,
    current_company: CurrentCompany,
    days: int = 7
) -> Any:
    """
    Get history of trip uploads.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    uploaded_at_col = cast(Any, Trip.uploaded_at)
    trip_date_col = cast(Any, Trip.trip_date)
    
    # Group trips by upload date and trip date
    stmt = (
        select(
            trip_date_col,
            func.date(uploaded_at_col).label("upload_date"),
            func.count(cast(Any, Trip.id)).label("trip_count"),
        )
        .where(Trip.company_id == current_company.id)
        .where(uploaded_at_col.is_not(None))
        .where(uploaded_at_col >= cutoff_date)
        .group_by(trip_date_col, func.date(uploaded_at_col))
        .order_by(desc(trip_date_col), desc(cast(Any, func.date(uploaded_at_col))))
    )
    
    results = session.exec(stmt).all()
    
    return [
        {
            "trip_date": trip_date.date().isoformat() if trip_date else None,
            "upload_date": upload_date.isoformat() if upload_date else None,
            "trips_uploaded": trip_count,
            "upload_lag_days": (
                (trip_date.date() - upload_date).days 
                if trip_date and upload_date else None
            )
        }
        for trip_date, upload_date, trip_count in results
    ]

# ============= MAP VISUALIZATION ENDPOINTS =============
@router_trips.get("/map/{date}", response_model=Dict)
async def get_trips_for_map(
    date: str,
    session: SessionDep,
    current_company: CurrentCompany
) -> Any:
    """
    Get trips with polylines for map visualization for a specific date.
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    trips = crud.get_trips_for_date_and_company(
        session=session,
        target_date=target_date,
        company_id=current_company.id,
        include_optimized=True
    )
    
    # Also get company's map markers
    markers_stmt = select(MapMarker).where(
        MapMarker.company_id == current_company.id,
        MapMarker.is_active == True
    )
    markers = session.exec(markers_stmt).all()
    
    # Calculate map bounds
    bounds = {
        "north": -90.0,
        "south": 90.0,
        "east": -180.0,
        "west": 180.0,
    }
    
    trip_data = []
    for trip in trips:
        trip_info = {
            "id": str(trip.id),
            "departure": {
                "name": trip.departure_point,
                "lat": trip.departure_lat,
                "lng": trip.departure_lng
            },
            "arrival": {
                "name": trip.arrival_point,
                "lat": trip.arrival_lat,
                "lng": trip.arrival_lng
            },
            "route_polyline": trip.route_polyline,
            "estimated_arrival": trip.estimated_arrival_datetime.isoformat() if trip.estimated_arrival_datetime else None,
            "status": trip.status,
            "optimized": bool(trip.assigned_vehicle_id),
            "sequence_order": trip.sequence_order
        }
        
        # Update bounds with trip coordinates
        if trip.departure_lat and trip.departure_lng:
            bounds["north"] = max(bounds["north"], trip.departure_lat)
            bounds["south"] = min(bounds["south"], trip.departure_lat)
            bounds["east"] = max(bounds["east"], trip.departure_lng)
            bounds["west"] = min(bounds["west"], trip.departure_lng)
        
        if trip.arrival_lat and trip.arrival_lng:
            bounds["north"] = max(bounds["north"], trip.arrival_lat)
            bounds["south"] = min(bounds["south"], trip.arrival_lat)
            bounds["east"] = max(bounds["east"], trip.arrival_lng)
            bounds["west"] = min(bounds["west"], trip.arrival_lng)
        
        trip_data.append(trip_info)
    
    marker_data = []
    for marker in markers:
        marker_info = {
            "id": str(marker.id),
            "name": marker.name,
            "lat": marker.lat,
            "lng": marker.lng,
            "type": marker.marker_type,
            "address": marker.address
        }
        
        # Update bounds with marker coordinates
        bounds["north"] = max(bounds["north"], marker.lat)
        bounds["south"] = min(bounds["south"], marker.lat)
        bounds["east"] = max(bounds["east"], marker.lng)
        bounds["west"] = min(bounds["west"], marker.lng)
        
        marker_data.append(marker_info)
    
    # If no coordinates found, use default bounds for Algeria
    if bounds["north"] == -90:
        bounds = {
            "north": 37.0,
            "south": 19.0,
            "east": 12.0,
            "west": -9.0
        }
    
    return {
        "trips": trip_data,
        "markers": marker_data,
        "bounds": bounds,
        "company": {
            "name": current_company.company_name,
            "depot": {
                "lat": current_company.depot_lat,
                "lng": current_company.depot_lng
            } if current_company.depot_lat and current_company.depot_lng else None
        }
    }

@router_trips.post("/map/create", response_model=TripPublic)
async def create_trip_from_map(
    session: SessionDep,
    current_company: CurrentCompany,
    departure_lat: float = Form(...),
    departure_lng: float = Form(...),
    departure_name: str = Form(...),
    arrival_lat: float = Form(...),
    arrival_lng: float = Form(...),
    arrival_name: str = Form(...),
    departure_time: str = Form(...),
    cargo_category: str = Form(...),
    cargo_weight_kg: Optional[float] = Form(None),
    cargo_weight: Optional[float] = Form(None),
    vehicle_id: Optional[uuid.UUID] = Form(None),
    required_vehicle_category: Optional[str] = Form(None)
) -> Any:
    """
    Create a trip by selecting points on the map.
    """
    try:
        departure_datetime = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")
    
    def parse_required_vehicle_category(raw: Optional[str]) -> Optional[VehicleCategory]:
        if not raw:
            return None
        try:
            return VehicleCategory(raw)
        except Exception:
            pass
        try:
            return VehicleCategory[raw]
        except Exception:
            return None

    def infer_required_vehicle_category_from_cargo(cargo: str) -> VehicleCategory:
        cargo_val = cargo.lower()
        if cargo_val.startswith("a01"):
            return VehicleCategory.AG1
        if cargo_val.startswith("a02"):
            return VehicleCategory.AG2
        if cargo_val.startswith("a03"):
            return VehicleCategory.AG3
        if cargo_val.startswith("a04"):
            return VehicleCategory.AG4
        if cargo_val.startswith("b01"):
            return VehicleCategory.BT1
        if cargo_val.startswith("b02"):
            return VehicleCategory.BT4
        if cargo_val.startswith("b03"):
            return VehicleCategory.BT3
        if cargo_val.startswith("i01"):
            return VehicleCategory.IN2
        if cargo_val.startswith("i02"):
            return VehicleCategory.IN6
        if cargo_val.startswith("c01"):
            return VehicleCategory.CH2
        if cargo_val.startswith("c02"):
            return VehicleCategory.CH4
        return VehicleCategory.AG1

    # Verify vehicle belongs to company (only if provided)
    if vehicle_id is not None:
        vehicle = session.get(Vehicle, vehicle_id)
        if not vehicle or vehicle.company_id != current_company.id:
            raise HTTPException(
                status_code=403,
                detail="Vehicle not found or does not belong to your company"
            )

    req_cat = parse_required_vehicle_category(required_vehicle_category)
    if req_cat is None:
        req_cat = infer_required_vehicle_category_from_cargo(cargo_category)
    
    # Calculate route using Valhalla
    valhalla = ValhallaService()
    route_data = await valhalla.get_route(
        start_lat=departure_lat,
        start_lng=departure_lng,
        end_lat=arrival_lat,
        end_lng=arrival_lng,
        departure_time=departure_datetime
    )
    
    await valhalla.close()
    
    # Create trip
    from app.models.trip_models import CargoCategory, MaterialType

    try:
        cargo_enum = CargoCategory(cargo_category)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cargo_category")

    weight_kg = cargo_weight_kg if cargo_weight_kg is not None else cargo_weight
    if weight_kg is None:
        raise HTTPException(status_code=400, detail="cargo_weight_kg is required")

    trip = Trip(
        company_id=current_company.id,
        departure_point=departure_name,
        departure_lat=departure_lat,
        departure_lng=departure_lng,
        arrival_point=arrival_name,
        arrival_lat=arrival_lat,
        arrival_lng=arrival_lng,
        departure_datetime=departure_datetime,
        arrival_datetime_planned=departure_datetime + timedelta(minutes=route_data.get("duration_min", 60)),
        cargo_category=cargo_enum,
        material_type=MaterialType.SOLID,
        cargo_weight_kg=weight_kg,
        required_vehicle_category=req_cat,
        route_polyline=route_data.get("polyline"),
        route_distance_km=route_data.get("distance_km"),
        route_duration_min=int(route_data.get("duration_min", 60)),
        created_from_map=True,
        map_session_id=str(uuid.uuid4()),
        vehicle_id=vehicle_id,
        trip_date=departure_datetime.replace(hour=0, minute=0, second=0, microsecond=0),
        uploaded_at=datetime.utcnow(),
        route_calculated=True
    )
    
    session.add(trip)
    session.commit()
    session.refresh(trip)
    
    return trip

@router_trips.get("/map/markers", response_model=List[Dict])
def get_company_markers(
    session: SessionDep,
    current_company: CurrentCompany
) -> Any:
    """
    Get all map markers (depots, warehouses) for a company.
    """
    markers_stmt = select(MapMarker).where(
        MapMarker.company_id == current_company.id,
        MapMarker.is_active == True
    ).order_by(desc(cast(Any, MapMarker.created_at)))
    
    markers = session.exec(markers_stmt).all()
    
    return [
        {
            "id": str(marker.id),
            "name": marker.name,
            "lat": marker.lat,
            "lng": marker.lng,
            "type": marker.marker_type,
            "address": marker.address,
            "created_at": marker.created_at.isoformat()
        }
        for marker in markers
    ]

@router_trips.post("/map/markers", response_model=Dict)
def create_map_marker(
    session: SessionDep,
    current_company: CurrentCompany,
    name: str = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    marker_type: str = Form("depot"),
    address: Optional[str] = Form(None)
) -> Any:
    """
    Save a marker on the map (depot, warehouse, etc.).
    """
    marker = MapMarker(
        company_id=current_company.id,
        name=name,
        lat=lat,
        lng=lng,
        marker_type=marker_type,
        address=address
    )
    
    session.add(marker)
    session.commit()
    session.refresh(marker)
    
    return {
        "id": str(marker.id),
        "name": marker.name,
        "lat": marker.lat,
        "lng": marker.lng,
        "type": marker.marker_type,
        "address": marker.address
    }

@router_trips.delete("/map/markers/{marker_id}")
def delete_map_marker(
    session: SessionDep,
    marker: CompanyMarker
) -> Message:
    """
    Delete a map marker.
    """
    marker_id = marker.id
    session.delete(marker)
    session.commit()
    
    return Message(message="Map marker deleted successfully")

# ============= NIGHTLY OPTIMIZATION ENDPOINT =============
@router_trips.post("/optimize/nightly", response_model=Dict)
def trigger_nightly_optimization(
    background_tasks: BackgroundTasks,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Trigger nightly optimization for tomorrow's trips (admin only).
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin only")
    
    # Calculate tomorrow's date
    tomorrow = datetime.utcnow() + timedelta(days=1)
    target_date = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Run in background
    background_tasks.add_task(
        run_nightly_optimization_task,
        session,
        target_date
    )
    
    return {
        "message": "Nightly optimization started",
        "target_date": target_date.date().isoformat(),
        "optimization_type": "cross_company",
        "estimated_completion": "02:00 AM",
        "note": "Optimization runs in background. Check optimization batches for results."
    }

async def run_nightly_optimization_task(session: Session, target_date: datetime):
    """
    Background task for nightly optimization.
    """
    try:
        from app.services.optimization import optimize_trips_for_date

        result = optimize_trips_for_date(
            session=session,
            target_date=target_date,
            company_id=None,
            optimization_type="cross_company",
        )
        
        if result.get("success"):
            # Send notifications to companies
            await send_optimization_notifications(session, result)
            
            logger.info(f"Nightly optimization completed for {target_date.date()}: {result}")
        else:
            logger.warning(f"Nightly optimization failed for {target_date.date()}: {result}")
            
    except Exception as e:
        logger.error(f"Nightly optimization error for {target_date.date()}: {str(e)}")

async def send_optimization_notifications(session: Session, result: Dict):
    """
    Send notifications to companies about optimization results.
    """
    # This would integrate with your notification system (email, SMS, etc.)
    # For now, just log
    logger.info(f"Optimization notifications would be sent for batch: {result.get('batch_id')}")

# ============= COMPANY KPIS ENDPOINT =============
@router_trips.get("/kpis/{date}", response_model=Dict)
def get_company_kpis(
    date: str,
    session: SessionDep,
    current_company: CurrentCompany
) -> Any:
    """
    Get KPIs for the company for a specific date.
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Get optimization batch for this date
    batch_stmt = select(OptimizationBatch).where(
        OptimizationBatch.batch_date == target_date,
        OptimizationBatch.optimization_type == "cross_company",
        OptimizationBatch.status == "completed"
    ).order_by(desc(cast(Any, OptimizationBatch.created_at)))
    
    batch = session.exec(batch_stmt).first()
    
    if not batch:
        return {
            "date": date,
            "optimized": False,
            "message": "No optimization found for this date"
        }
    
    # Get company's optimization result
    result_stmt = select(CompanyOptimizationResult).where(
        CompanyOptimizationResult.optimization_batch_id == batch.id,
        CompanyOptimizationResult.company_id == current_company.id
    )
    result = session.exec(result_stmt).first()
    
    if not result:
        return {
            "date": date,
            "optimized": False,
            "message": "Company did not participate in optimization for this date"
        }
    
    # Get total trips for this date
    total_trips = crud.get_trip_count_by_date(
        session=session,
        company_id=current_company.id,
        target_date=target_date.date()
    )
    
    optimization_rate = (result.trips_assigned / total_trips * 100) if total_trips > 0 else 0
    
    return {
        "date": date,
        "optimized": True,
        "batch_id": str(batch.id),
        "summary": {
            "trips_contributed": result.trips_contributed,
            "trips_assigned": result.trips_assigned,
            "optimization_rate": round(optimization_rate, 1),
            "vehicles_used": result.vehicles_used,
            "vehicles_borrowed": result.vehicles_borrowed,
            "vehicles_shared_out": result.vehicles_shared_out
        },
        "savings": {
            "km_saved": round(result.km_saved, 2),
            "fuel_saved_liters": round(result.fuel_saved_liters, 2),
            "co2_saved_kg": round(result.co2_saved_kg, 2),
            "cost_saved_usd": round(result.cost_saved_usd, 2)
        },
        "efficiency": {
            "km_per_vehicle": round(result.km_saved / max(1, result.vehicles_used), 2),
            "fuel_efficiency": round(result.fuel_saved_liters / max(1, result.trips_assigned), 2),
            "cost_per_trip": round(result.cost_saved_usd / max(1, result.trips_assigned), 2)
        }
    }

@router_trips.get("/optimized-plan/{date}", response_model=Dict)
def get_optimized_trip_plan(
    date: str,
    session: SessionDep,
    current_company: CurrentCompany
) -> Any:
    """
    Get the optimized trip plan for a company after nightly optimization.
    This is what drivers would receive in the morning.
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Get optimized trips for this date
    trips = crud.get_optimized_trips_for_date(
        session=session,
        company_id=current_company.id,
        target_date=target_date
    )
    
    if not trips:
        return {
            "company": current_company.company_name,
            "date": date,
            "message": "No optimized trips found for this date",
            "total_trips": 0,
            "total_vehicles_assigned": 0,
            "driver_assignments": []
        }
    
    # Group by vehicle for driver assignments
    from collections import defaultdict
    vehicle_assignments = defaultdict(list)
    for trip in trips:
        if trip.assigned_vehicle_id:
            vehicle_assignments[str(trip.assigned_vehicle_id)].append(trip)
    
    # Create driver plan
    driver_plan = []
    for vehicle_id, vehicle_trips in vehicle_assignments.items():
        # Sort by sequence order
        vehicle_trips.sort(key=lambda x: x.sequence_order or 0)
        
        # Get vehicle details
        vehicle = session.get(Vehicle, uuid.UUID(vehicle_id))
        
        # Calculate route for the entire chain
        total_distance = sum(t.route_distance_km or 0 for t in vehicle_trips)
        total_duration = sum(t.route_duration_min or 0 for t in vehicle_trips)
        
        # Add return distance for last trip
        last_trip = vehicle_trips[-1]
        if last_trip.is_last_in_chain and last_trip.return_distance_km:
            total_distance += last_trip.return_distance_km
            total_duration += last_trip.return_duration_min or 0
        
        driver_plan.append({
            "vehicle_id": vehicle_id,
            "license_plate": vehicle.license_plate if vehicle else "Unknown",
            "vehicle_category": vehicle.category.value if vehicle else "Unknown",
            "driver_assignment": "To be assigned",  # Would come from driver management
            "trip_chain": [
                {
                    "sequence": trip.sequence_order or idx + 1,
                    "trip_id": str(trip.id),
                    "departure": trip.departure_point,
                    "arrival": trip.arrival_point,
                    "departure_time": trip.departure_datetime.isoformat(),
                    "estimated_arrival": trip.estimated_arrival_datetime.isoformat() if trip.estimated_arrival_datetime else None,
                    "cargo": trip.cargo_category.value,
                    "weight_kg": trip.cargo_weight_kg,
                    "status": trip.status
                }
                for idx, trip in enumerate(vehicle_trips)
            ],
            "chain_summary": {
                "total_distance_km": round(total_distance, 2),
                "total_duration_min": round(total_duration, 2),
                "number_of_stops": len(vehicle_trips),
                "start_time": vehicle_trips[0].departure_datetime.isoformat(),
                "estimated_completion": (
                    vehicle_trips[0].departure_datetime + timedelta(minutes=total_duration)
                ).isoformat()
            }
        })
    
    return {
        "company": current_company.company_name,
        "date": date,
        "total_trips": len(trips),
        "total_vehicles_assigned": len(vehicle_assignments),
        "driver_assignments": driver_plan,
        "optimization_notes": "Generated by nightly cross-company optimization. Check individual trip details for specific instructions."
    }

# ============= DASHBOARD ENDPOINTS =============
@router_trips.get("/dashboard/date/{date}", response_model=DashboardMetrics)
def read_dashboard_by_date(
    date: str,
    session: SessionDep,
    current_company: CurrentCompany
) -> Any:
    """
    Get dashboard metrics for a specific date.
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Get trips for this date
    company_trips = crud.get_trips_for_date_and_company(
        session=session,
        target_date=target_date,
        company_id=current_company.id,
        include_optimized=True
    )
    
    # Calculate metrics
    trips_in_progress = len([t for t in company_trips if t.status == TripStatus.IN_PROGRESS])
    
    # Vehicles used today (unique vehicle IDs from trips)
    vehicle_ids = set()
    for trip in company_trips:
        if trip.assigned_vehicle_id:
            vehicle_ids.add(trip.assigned_vehicle_id)
        elif trip.vehicle_id:
            vehicle_ids.add(trip.vehicle_id)
    
    vehicles_distributed = len(vehicle_ids)
    
    # KM and fuel saved (from optimization batch if available)
    km_reduced = 0.0
    fuel_saved = 0.0
    
    # Get latest optimization batch for this date
    batch_stmt = select(OptimizationBatch).where(
        OptimizationBatch.batch_date == target_date,
        OptimizationBatch.status == "completed"
    ).order_by(desc(cast(Any, OptimizationBatch.created_at)))
    
    latest_batch = session.exec(batch_stmt).first()
    
    if latest_batch:
        # Get company-specific results
        result_stmt = select(CompanyOptimizationResult).where(
            CompanyOptimizationResult.optimization_batch_id == latest_batch.id,
            CompanyOptimizationResult.company_id == current_company.id
        )
        company_result = session.exec(result_stmt).first()
        
        if company_result:
            km_reduced = company_result.km_saved or 0.0
            fuel_saved = company_result.fuel_saved_liters or 0.0
    
    # ESG contribution (CO2 saved)
    # Average: 2.68 kg CO2 per liter of diesel
    co2_saved_kg = fuel_saved * 2.68
    
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

@router_trips.get("/dashboard/overview", response_model=Dict)
def get_company_overview(
    session: SessionDep,
    current_company: CurrentCompany,
    period: str = "week"  # week, month, quarter
) -> Any:
    """
    Get overview of company performance and optimization benefits.
    """
    # Calculate period dates
    end_date: datetime = datetime.utcnow()
    if period == "week":
        start_date: datetime = end_date - timedelta(days=7)
    elif period == "month":
        start_date = end_date - timedelta(days=30)
    else:  # quarter
        start_date = end_date - timedelta(days=90)
    
    # Get optimization results for period
    result_stmt = (
        select(CompanyOptimizationResult)
        .join(OptimizationBatch)
        .where(CompanyOptimizationResult.company_id == current_company.id)
        .where(OptimizationBatch.batch_date >= start_date)
        .where(OptimizationBatch.batch_date <= end_date)
        .where(OptimizationBatch.status == "completed")
    )
    results = session.exec(result_stmt).all()
    
    # Calculate totals
    totals = {
        "trips_optimized": sum(r.trips_assigned for r in results),
        "km_saved": sum(r.km_saved for r in results),
        "fuel_saved": sum(r.fuel_saved_liters for r in results),
        "co2_saved": sum(r.co2_saved_kg for r in results),
        "cost_saved": sum(r.cost_saved_usd for r in results),
        "vehicles_borrowed": sum(r.vehicles_borrowed for r in results),
        "vehicles_shared_out": sum(r.vehicles_shared_out for r in results)
    }
    
    # Get recent trips
    recent_trips_stmt = select(Trip).where(
        Trip.company_id == current_company.id
    ).order_by(desc(cast(Any, Trip.departure_datetime))).limit(10)
    
    recent_trips = session.exec(recent_trips_stmt).all()
    
    # Get optimization rate
    total_trips_stmt = select(func.count(cast(Any, Trip.id))).where(
        Trip.company_id == current_company.id,
        cast(Any, Trip.departure_datetime) >= start_date,
        cast(Any, Trip.departure_datetime) <= end_date,
    )
    total_trips = session.exec(total_trips_stmt).first() or 0
    
    optimization_rate = (totals["trips_optimized"] / total_trips * 100) if total_trips > 0 else 0
    
    return {
        "company": current_company.company_name,
        "period": period,
        "dates": {
            "start": start_date.date().isoformat(),
            "end": end_date.date().isoformat()
        },
        "summary": {
            "total_trips": total_trips,
            "trips_optimized": totals["trips_optimized"],
            "optimization_rate": round(optimization_rate, 1),
            "average_savings_per_trip": {
                "km": round(totals["km_saved"] / max(1, totals["trips_optimized"]), 2),
                "fuel_liters": round(totals["fuel_saved"] / max(1, totals["trips_optimized"]), 2),
                "cost_usd": round(totals["cost_saved"] / max(1, totals["trips_optimized"]), 2)
            }
        },
        "savings": {
            "total_km_saved": round(totals["km_saved"], 2),
            "total_fuel_saved": round(totals["fuel_saved"], 2),
            "total_co2_saved": round(totals["co2_saved"], 2),
            "total_cost_saved": round(totals["cost_saved"], 2),
            "equivalent_trees": int(totals["co2_saved"] / 21)  # 1 tree absorbs 21kg CO2/year
        },
        "collaboration": {
            "vehicles_borrowed": totals["vehicles_borrowed"],
            "vehicles_shared_out": totals["vehicles_shared_out"],
            "estimated_partner_savings": round(totals["cost_saved"] * 0.3, 2),  # Estimated partner savings
            "platform_contribution": round(totals["co2_saved"] / 1000, 2)  # Metric tons CO2 saved
        },
        "recent_activity": [
            {
                "date": trip.departure_datetime.date().isoformat(),
                "route": f"{trip.departure_point} → {trip.arrival_point}",
                "status": trip.status,
                "optimized": bool(trip.optimization_batch_id),
                "savings": (trip.route_distance_km or 0) * 0.3 if trip.route_distance_km else 0  # Estimated fuel savings
            }
            for trip in recent_trips
        ]
    }