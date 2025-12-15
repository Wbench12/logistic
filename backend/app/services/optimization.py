import uuid
from typing import Dict, List, Any, Optional, cast
from datetime import datetime

from sqlmodel import Session, select


def optimize_trips_for_date(
    *,
    session: Session,
    target_date: datetime,
    company_id: Optional[uuid.UUID] = None,
    optimization_type: str = "cross_company",
) -> Dict[str, Any]:
    """Entry point used by the trips routes.

    - `cross_company`: delegates to `CrossCompanyOptimizationService`.
    - `single_company`: performs a simple in-company assignment for the day.
    """
    optimization_type = (optimization_type or "").strip().lower() or "cross_company"

    if optimization_type == "cross_company":
        from app.services.cross_company_optimization import CrossCompanyOptimizationService
        import asyncio

        service = CrossCompanyOptimizationService()
        try:
            return asyncio.run(service.run_nightly_optimization(session=session, target_date=target_date))
        finally:
            try:
                asyncio.run(service.close())
            except Exception:
                pass

    if optimization_type != "single_company":
        return {"success": False, "error": f"Unknown optimization_type: {optimization_type}"}

    if company_id is None:
        return {"success": False, "error": "company_id is required for single_company optimization"}

    from app.models.trip_models import OptimizationBatch, OptimizationBatchStatus, Trip
    from app.models.company_models import Vehicle, VehicleStatus, VehicleCategory
    from app.models.trip_models import TripStatus as DbTripStatus

    batch = OptimizationBatch(
        batch_date=target_date,
        status=OptimizationBatchStatus.PROCESSING,
        optimization_type="single_company",
        total_trips=0,
        created_at=datetime.utcnow(),
        participating_companies=[company_id],
        total_companies=1,
    )
    session.add(batch)
    session.commit()
    session.refresh(batch)

    try:
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        assigned_vehicle_id_col = cast(Any, Trip.assigned_vehicle_id)
        trips = session.exec(
            select(Trip)
            .where(cast(Any, Trip.company_id) == company_id)
            .where(cast(Any, Trip.departure_datetime) >= start_of_day)
            .where(cast(Any, Trip.departure_datetime) <= end_of_day)
            .where(cast(Any, Trip.status) == DbTripStatus.PLANNED)
            .where(assigned_vehicle_id_col.is_(None))
        ).all()

        vehicles = session.exec(
            select(Vehicle)
            .where(cast(Any, Vehicle.company_id) == company_id)
            .where(cast(Any, Vehicle.is_active) == True)
            .where(cast(Any, Vehicle.status) == VehicleStatus.AVAILABLE)
        ).all()

        if not trips or not vehicles:
            batch.status = OptimizationBatchStatus.COMPLETED
            batch.total_trips = 0
            session.add(batch)
            session.commit()
            return {
                "success": False,
                "batch_id": str(batch.id),
                "message": "No trips or vehicles available for optimization",
            }

        def infer_required_vehicle_category(trip: Trip) -> VehicleCategory:
            if trip.required_vehicle_category is not None:
                return trip.required_vehicle_category
            cargo_val = (getattr(trip.cargo_category, "value", None) or str(trip.cargo_category)).lower()
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

        from app.models.company_models import Company
        from app.services.valhalla_service import ValhallaService

        company = session.get(Company, company_id)

        def _vehicle_depot_coords(vehicle: Vehicle) -> Optional[tuple[float, float]]:
            lat = getattr(vehicle, "depot_lat", None)
            lng = getattr(vehicle, "depot_lng", None)
            if lat is not None and lng is not None:
                return (float(lat), float(lng))
            if company is not None and company.depot_lat is not None and company.depot_lng is not None:
                return (float(company.depot_lat), float(company.depot_lng))
            return None

        def _is_vehicle_compatible(vehicle: Vehicle, trip: Trip, required_cat: VehicleCategory) -> bool:
            if vehicle.category != required_cat:
                return False

            # Capacity constraints are per-trip (each trip's shipment must fit the vehicle)
            if vehicle.capacity_tons is not None:
                capacity_kg = float(vehicle.capacity_tons) * 1000.0
                if float(trip.cargo_weight_kg) > capacity_kg:
                    return False
            if trip.cargo_volume_m3 is not None and vehicle.capacity_m3 is not None:
                if float(trip.cargo_volume_m3) > float(vehicle.capacity_m3):
                    return False
            return True

        def _trip_has_coords(trip: Trip) -> bool:
            return (
                trip.departure_lat is not None
                and trip.departure_lng is not None
                and trip.arrival_lat is not None
                and trip.arrival_lng is not None
            )

        def _trip_duration_seconds(trip: Trip) -> int:
            if trip.route_duration_min is not None:
                return max(0, int(float(trip.route_duration_min) * 60))
            # Best-effort compute (Valhalla route + fallback haversine)
            calc = calculate_trip_distance_and_duration(trip)
            if calc and calc.get("duration_min") is not None:
                return max(0, int(float(calc["duration_min"]) * 60))
            return 60 * 60

        def _coord_key(lat: float, lng: float) -> tuple[float, float]:
            return (round(float(lat), 6), round(float(lng), 6))

        async def _solve_group(
            *,
            group_trips: list[Trip],
            group_vehicles: list[Vehicle],
            required_cat: VehicleCategory,
        ) -> tuple[dict[uuid.UUID, list[Trip]], list[Trip], dict[str, Any]]:
            """Solve a direct-shipment day routing problem.

            Nodes are trips; arc costs are deadhead travel time (arrival->next departure)
            plus the next trip's own travel time (departure->arrival).
            """

            feasible_trips: list[Trip] = []
            infeasible_trips: list[Trip] = []

            compatible_vehicle_indices_by_trip_id: dict[uuid.UUID, list[int]] = {}
            depots: list[tuple[float, float]] = []

            for v in group_vehicles:
                depot = _vehicle_depot_coords(v)
                depots.append(depot if depot is not None else (0.0, 0.0))

            for t in group_trips:
                if not _trip_has_coords(t):
                    infeasible_trips.append(t)
                    continue

                compatible = [idx for idx, v in enumerate(group_vehicles) if _is_vehicle_compatible(v, t, required_cat)]
                if not compatible:
                    infeasible_trips.append(t)
                    continue
                compatible_vehicle_indices_by_trip_id[t.id] = compatible
                feasible_trips.append(t)

            if not feasible_trips or not group_vehicles:
                return {}, infeasible_trips + feasible_trips, {"success": False, "message": "No feasible trips/vehicles"}

            # Build location index for Valhalla matrix
            location_index: dict[tuple[float, float], int] = {}
            locations: list[tuple[float, float]] = []

            def add_location(lat: float, lng: float) -> int:
                key = _coord_key(lat, lng)
                if key in location_index:
                    return location_index[key]
                location_index[key] = len(locations)
                locations.append(key)
                return location_index[key]

            for i, (depot_lat, depot_lng) in enumerate(depots):
                # If we had no depot coordinates, fall back to first trip departure to keep matrix finite
                if depot_lat == 0.0 and depot_lng == 0.0:
                    first = feasible_trips[0]
                    assert first.departure_lat is not None and first.departure_lng is not None
                    depots[i] = (float(first.departure_lat), float(first.departure_lng))
                    depot_lat, depot_lng = depots[i]
                add_location(depot_lat, depot_lng)

            for t in feasible_trips:
                assert t.departure_lat is not None and t.departure_lng is not None
                assert t.arrival_lat is not None and t.arrival_lng is not None
                add_location(float(t.departure_lat), float(t.departure_lng))
                add_location(float(t.arrival_lat), float(t.arrival_lng))

            valhalla = ValhallaService()
            try:
                matrix = await valhalla.get_matrix(locations)
            finally:
                await valhalla.close()

            durations = matrix["durations"]
            matrix_meta = {
                "matrix_success": bool(matrix.get("success")),
                "matrix_fallback": bool(matrix.get("fallback")),
                "locations": len(locations),
            }

            def travel_time_seconds(from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> int:
                from_idx = location_index.get(_coord_key(from_lat, from_lng))
                to_idx = location_index.get(_coord_key(to_lat, to_lng))
                if from_idx is None or to_idx is None:
                    return 0
                try:
                    return max(0, int(float(durations[from_idx][to_idx])))
                except Exception:
                    return 0

            trip_duration_seconds: dict[uuid.UUID, int] = {t.id: _trip_duration_seconds(t) for t in feasible_trips}

            # OR-Tools routing model
            from ortools.constraint_solver import pywrapcp, routing_enums_pb2  # type: ignore[import-untyped]

            n_trips = len(feasible_trips)
            n_vehicles = len(group_vehicles)
            # Nodes: [trip0..tripN-1, depot0..depotK-1]
            node_count = n_trips + n_vehicles
            starts = [n_trips + i for i in range(n_vehicles)]
            ends = [n_trips + i for i in range(n_vehicles)]

            manager = pywrapcp.RoutingIndexManager(node_count, n_vehicles, starts, ends)
            routing = pywrapcp.RoutingModel(manager)

            def node_is_trip(node: int) -> bool:
                return node < n_trips

            def depot_coords(vehicle_index: int) -> tuple[float, float]:
                return depots[vehicle_index]

            def from_coords(node: int) -> tuple[float, float]:
                if node_is_trip(node):
                    t = feasible_trips[node]
                    assert t.arrival_lat is not None and t.arrival_lng is not None
                    return (float(t.arrival_lat), float(t.arrival_lng))
                vehicle_index = node - n_trips
                return depot_coords(vehicle_index)

            def to_coords(node: int) -> tuple[float, float]:
                if node_is_trip(node):
                    t = feasible_trips[node]
                    assert t.departure_lat is not None and t.departure_lng is not None
                    return (float(t.departure_lat), float(t.departure_lng))
                vehicle_index = node - n_trips
                return depot_coords(vehicle_index)

            def transit_time_callback(from_index: int, to_index: int) -> int:
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                f_lat, f_lng = from_coords(from_node)
                t_lat, t_lng = to_coords(to_node)
                base = travel_time_seconds(f_lat, f_lng, t_lat, t_lng)
                if node_is_trip(to_node):
                    base += trip_duration_seconds[feasible_trips[to_node].id]
                return base

            transit_index = routing.RegisterTransitCallback(transit_time_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_index)

            # Restrict depot nodes to their own vehicle
            for v_idx in range(n_vehicles):
                depot_node = n_trips + v_idx
                routing.SetAllowedVehiclesForIndex([v_idx], manager.NodeToIndex(depot_node))

            # Restrict trip nodes to compatible vehicles
            for trip_node, trip in enumerate(feasible_trips):
                allowed = compatible_vehicle_indices_by_trip_id.get(trip.id, [])
                if allowed:
                    routing.SetAllowedVehiclesForIndex(allowed, manager.NodeToIndex(trip_node))
                # allow dropping if needed (large penalty)
                routing.AddDisjunction([manager.NodeToIndex(trip_node)], 1_000_000_000)

            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            search_parameters.time_limit.FromSeconds(10)

            solution = routing.SolveWithParameters(search_parameters)
            if solution is None:
                return {}, infeasible_trips + feasible_trips, {"success": False, "message": "No solution", **matrix_meta}

            routes: dict[uuid.UUID, list[Trip]] = {}
            assigned_trip_ids: set[uuid.UUID] = set()

            for v_idx, vehicle in enumerate(group_vehicles):
                index = routing.Start(v_idx)
                vehicle_route: list[Trip] = []
                while not routing.IsEnd(index):
                    node = manager.IndexToNode(index)
                    if node_is_trip(node):
                        trip = feasible_trips[node]
                        vehicle_route.append(trip)
                        assigned_trip_ids.add(trip.id)
                    index = solution.Value(routing.NextVar(index))

                if vehicle_route:
                    routes[vehicle.id] = vehicle_route

            dropped = [t for t in feasible_trips if t.id not in assigned_trip_ids]
            return routes, infeasible_trips + dropped, {"success": True, **matrix_meta}

        # Group by required vehicle category
        trips_by_cat: dict[VehicleCategory, list[Trip]] = {}
        for t in trips:
            trips_by_cat.setdefault(infer_required_vehicle_category(t), []).append(t)

        vehicles_by_cat: dict[VehicleCategory, list[Vehicle]] = {}
        for v in vehicles:
            vehicles_by_cat.setdefault(v.category, []).append(v)

        import asyncio

        assignments: list[dict[str, Any]] = []
        unassigned: list[dict[str, Any]] = []
        used_vehicle_ids: set[uuid.UUID] = set()
        matrix_info: dict[str, Any] = {}

        for cat, cat_trips in trips_by_cat.items():
            cat_vehicles = vehicles_by_cat.get(cat, [])
            if not cat_vehicles:
                for t in cat_trips:
                    unassigned.append({"trip_id": str(t.id), "reason": f"no_vehicles_for_category:{cat.value}"})
                continue

            routes, dropped_trips, meta = asyncio.run(
                _solve_group(group_trips=cat_trips, group_vehicles=cat_vehicles, required_cat=cat)
            )
            matrix_info.setdefault(cat.value, meta)

            for trip in dropped_trips:
                unassigned.append({"trip_id": str(trip.id), "reason": "dropped_or_infeasible"})

            for vehicle_id, route_trips in routes.items():
                used_vehicle_ids.add(vehicle_id)
                for idx, trip in enumerate(route_trips, start=1):
                    trip.optimization_batch_id = batch.id
                    trip.assigned_vehicle_id = vehicle_id
                    trip.sequence_order = idx
                    trip.is_last_in_chain = idx == len(route_trips)
                    trip.optimization_status = "assigned"
                    trip.updated_at = datetime.utcnow()
                    session.add(trip)
                    assignments.append(
                        {
                            "trip_id": str(trip.id),
                            "assigned_vehicle_id": str(vehicle_id),
                            "sequence_order": idx,
                            "is_last_in_chain": idx == len(route_trips),
                            "required_vehicle_category": cat.value,
                        }
                    )

        batch.status = OptimizationBatchStatus.COMPLETED
        batch.completed_at = datetime.utcnow()
        batch.total_trips = len(assignments)
        batch.vehicles_used = len(used_vehicle_ids)
        session.add(batch)
        session.commit()

        return {
            "success": True,
            "batch_id": str(batch.id),
            "trips_optimized": len(assignments),
            "vehicles_used": len(used_vehicle_ids),
            "assignments": assignments,
            "unassigned": unassigned,
            "valhalla_matrix": matrix_info,
        }
    except Exception as exc:
        batch.status = OptimizationBatchStatus.FAILED
        session.add(batch)
        session.commit()
        return {"success": False, "batch_id": str(batch.id), "error": str(exc)}


def calculate_trip_distance_and_duration(
    trip: Any,
    *,
    start_lat: Optional[float] = None,
    start_lng: Optional[float] = None,
    end_lat: Optional[float] = None,
    end_lng: Optional[float] = None,
    base_url: str = "http://localhost:8002",
) -> Optional[Dict[str, Any]]:
    """Synchronous Valhalla routing helper used by the create-trip route."""
    import httpx
    import math
    import polyline as pl

    s_lat = start_lat if start_lat is not None else getattr(trip, "departure_lat", None)
    s_lng = start_lng if start_lng is not None else getattr(trip, "departure_lng", None)
    e_lat = end_lat if end_lat is not None else getattr(trip, "arrival_lat", None)
    e_lng = end_lng if end_lng is not None else getattr(trip, "arrival_lng", None)

    if s_lat is None or s_lng is None or e_lat is None or e_lng is None:
        return None

    request_body: Dict[str, Any] = {
        "locations": [
            {"lat": float(s_lat), "lon": float(s_lng)},
            {"lat": float(e_lat), "lon": float(e_lng)},
        ],
        "costing": "truck",
        "directions_options": {"units": "kilometers"},
    }

    def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * r * math.asin(math.sqrt(a))

    try:
        resp = httpx.post(f"{base_url}/route", json=request_body, timeout=30.0)
        if resp.status_code == 200:
            data = resp.json()
            leg = data["trip"]["legs"][0]
            return {
                "distance_km": leg["summary"]["length"] / 1000,
                "duration_min": int(leg["summary"]["time"] / 60),
                "polyline": data["trip"]["legs"][0]["shape"],
                "success": True,
            }
    except Exception:
        pass

    # Fallback
    distance = haversine_km(float(s_lat), float(s_lng), float(e_lat), float(e_lng))
    return {
        "distance_km": distance,
        "duration_min": int(distance / 40 * 60),
        "polyline": pl.encode([(float(s_lat), float(s_lng)), (float(e_lat), float(e_lng))]),
        "success": False,
        "fallback": True,
    }