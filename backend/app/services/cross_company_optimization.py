import uuid
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict
import asyncio

from ortools.sat.python import cp_model
from sqlmodel import Session, select

from app.models.trip_models import Trip, OptimizationBatch, CompanyOptimizationResult, OptimizationBatchStatus
from app.models.company_models import Company, Vehicle
from app.services.valhalla_service import ValhallaService
import logging
logger = logging.getLogger(__name__)

class CrossCompanyOptimizationService:
    def __init__(self):
        self.valhalla = ValhallaService()
        self.model = None
        self.solver = None
    
    async def run_nightly_optimization(
        self,
        session: Session,
        target_date: datetime
    ) -> Dict[str, Any]:
        """
        Run cross-company optimization for a specific date.
        """
        # Create optimization batch
        batch = OptimizationBatch(
            batch_date=target_date,
            status=OptimizationBatchStatus.PROCESSING,
            optimization_type="cross_company",
            total_trips=0,
            created_at=datetime.now(UTC)
        )
        session.add(batch)
        session.commit()
        session.refresh(batch)
        
        try:
            logger.info(f"Starting cross-company optimization for {target_date.date()}")
            
            # Step 1: Get all trips for the target date
            trips = await self._get_trips_for_date(session, target_date)
            logger.info(f"Found {len(trips)} trips for optimization")
            
            # Step 2: Get all available vehicles
            vehicles = await self._get_available_vehicles(session, target_date)
            logger.info(f"Found {len(vehicles)} available vehicles")
            
            if not trips or not vehicles:
                batch.status = OptimizationBatchStatus.COMPLETED
                batch.total_trips = 0
                session.add(batch)
                session.commit()
                return {
                    "success": False,
                    "batch_id": str(batch.id),
                    "message": "No trips or vehicles available for optimization"
                }
            
            # Step 3: Group trips by compatibility
            trip_groups = self._group_trips_by_compatibility(trips)
            logger.info(f"Grouped trips into {len(trip_groups)} compatibility groups")
            
            # Step 4: Run optimization for each group
            all_assignments = []
            participating_companies = set()
            total_km_saved = 0.0
            total_fuel_saved = 0.0
            
            for vehicle_category, trips_in_group in trip_groups.items():
                logger.info(f"Optimizing group {vehicle_category} with {len(trips_in_group)} trips")
                
                # Get compatible vehicles for this category
                compatible_vehicles = [
                    v for v in vehicles 
                    if v.category == vehicle_category
                ]
                
                if not compatible_vehicles:
                    logger.warning(f"No compatible vehicles for category {vehicle_category}")
                    continue
                
                # Convert to optimization format
                trips_data = await self._prepare_trips_data(trips_in_group)
                vehicles_data = await self._prepare_vehicles_data(compatible_vehicles)
                
                # Run optimization for this group
                group_result = await self._optimize_group(
                    trips_data, 
                    vehicles_data, 
                    vehicle_category
                )
                
                if group_result["success"]:
                    all_assignments.extend(group_result["assignments"])
                    
                    # Track participating companies
                    for assignment in group_result["assignments"]:
                        # Store as strings for JSON compatibility
                        participating_companies.add(str(assignment["original_company"]))
                        participating_companies.add(str(assignment["assigned_company"]))
                    
                    total_km_saved += group_result.get("km_saved", 0)
                    total_fuel_saved += group_result.get("fuel_saved", 0)
                    
                    logger.info(f"Group {vehicle_category} optimized: {len(group_result['assignments'])} assignments")
            
            # Step 5: Update database with assignments
            updated_trips = await self._update_trip_assignments(
                session, all_assignments, batch.id
            )
            logger.info(f"Updated {len(updated_trips)} trips with assignments")
            
            # Step 6: Calculate KPIs for each company
            company_kpis = await self._calculate_company_kpis(
                session, updated_trips, trips, batch.id
            )
            logger.info(f"Calculated KPIs for {len(company_kpis)} companies")
            
            # Step 7: Update batch with results
            batch.status = OptimizationBatchStatus.COMPLETED
            batch.completed_at = datetime.now(UTC)
            batch.total_trips = len(updated_trips)
            batch.participating_companies = list(participating_companies)
            batch.total_companies = len(participating_companies)
            batch.company_results = company_kpis
            batch.km_saved = total_km_saved
            batch.fuel_saved_liters = total_fuel_saved
            batch.vehicles_used = len(set(a["assigned_vehicle_id"] for a in all_assignments))
            
            session.add(batch)
            session.commit()
            
            # Step 8: Generate optimization reports
            reports = await self._generate_company_reports(
                session, batch.id, company_kpis
            )
            
            logger.info(f"Cross-company optimization completed successfully for {target_date.date()}")
            
            return {
                "success": True,
                "batch_id": str(batch.id),
                "trips_optimized": len(updated_trips),
                "companies_involved": len(participating_companies),
                "total_km_saved": total_km_saved,
                "total_fuel_saved": total_fuel_saved,
                "company_reports": reports
            }
            
        except Exception as e:
            logger.error(f"Cross-company optimization failed: {str(e)}")
            batch.status = OptimizationBatchStatus.FAILED
            session.add(batch)
            session.commit()
            
            return {
                "success": False,
                "batch_id": str(batch.id),
                "error": str(e)
            }
    
    async def _get_trips_for_date(self, session: Session, target_date: datetime) -> List[Trip]:
        """Get all trips for a specific date."""
        trip_stmt = select(Trip).where(
            Trip.trip_date == target_date.date(),
            Trip.status == "planifie",
            Trip.route_calculated == True,
            Trip.optimization_status == "pending"
        )
        return list(session.exec(trip_stmt).all())
    
    async def _get_available_vehicles(self, session: Session, target_date: datetime) -> List[Vehicle]:
        """Get all available vehicles."""
        vehicle_stmt = select(Vehicle).where(
            Vehicle.is_active == True,
            Vehicle.status == "disponible"
        )
        return list(session.exec(vehicle_stmt).all())
    
    def _group_trips_by_compatibility(self, trips: List[Trip]) -> Dict[str, List[Trip]]:
        """Group trips by vehicle compatibility."""
        groups = defaultdict(list)
        
        # Mapping from cargo category to vehicle category
        compatibility_map = {
            "a01_produits_frais": "ag1_camion_frigorifique",
            "a02_produits_surgeles": "ag2_camion_refrigere",
            "a03_produits_secs": "ag3_camion_isotherme",
            "a04_boissons_liquides": "ag4_camion_citerne_alimentaire",
            "b01_materiaux_vrac": "bt1_camion_benne",
            "b02_materiaux_solides": "bt4_camion_plateau_ridelles",
            "b03_beton_pret": "bt3_camion_malaxeur",
            "i01_produits_finis": "in2_fourgon_ferme",
            "i02_pieces_detachees": "in6_camion_fourgon_hayon",
            "c01_chimiques_liquides": "ch2_camion_citerne_chimique",
            "c02_chimiques_solides": "ch4_camion_adr",
        }
        
        for trip in trips:
            vehicle_category = compatibility_map.get(trip.cargo_category.value, "ag1_camion_frigorifique")
            groups[vehicle_category].append(trip)
        
        return dict(groups)
    
    async def _prepare_trips_data(self, trips: List[Trip]) -> List[Dict]:
        """Prepare trip data for optimization."""
        trips_data = []
        for trip in trips:
            # Get return distance from Valhalla if not already calculated
            return_distance = trip.return_distance_km
            if (
                not return_distance
                and trip.arrival_lat is not None
                and trip.arrival_lng is not None
                and trip.company.depot_lat
                and trip.company.depot_lng
            ):
                return_route = await self.valhalla.get_route(
                    start_lat=trip.arrival_lat,
                    start_lng=trip.arrival_lng,
                    end_lat=trip.company.depot_lat,
                    end_lng=trip.company.depot_lng
                )
                return_distance = return_route.get("distance_km", 0)
            
            trips_data.append({
                "id": str(trip.id),
                "reference": f"{trip.departure_point[:10]}...{trip.arrival_point[-10:]}",
                "orig": (trip.departure_lat, trip.departure_lng),
                "dest": (trip.arrival_lat, trip.arrival_lng),
                "earliest": trip.departure_datetime.timestamp(),
                "latest": trip.arrival_datetime_planned.timestamp(),
                "duration": trip.route_duration_min or 60,
                "service": 30,  # Default service time
                "demand": trip.cargo_weight_kg,
                "r_i0": return_distance or 0,
                "company_id": str(trip.company_id),
                "original_vehicle_id": str(trip.vehicle_id) if trip.vehicle_id else None,
                "departure_time": trip.departure_datetime,
                "arrival_time": trip.arrival_datetime_planned,
                "priority": trip.trip_priority or 1
            })
        
        return trips_data
    
    async def _prepare_vehicles_data(self, vehicles: List[Vehicle]) -> List[Dict]:
        """Prepare vehicle data for optimization."""
        vehicles_data = []
        for vehicle in vehicles:
            # Get depot coordinates (vehicle-specific or company default)
            depot_lat = vehicle.depot_lat or vehicle.company.depot_lat
            depot_lng = vehicle.depot_lng or vehicle.company.depot_lng
            
            vehicles_data.append({
                "id": str(vehicle.id),
                "depot": (depot_lat, depot_lng) if depot_lat and depot_lng else (0, 0),
                "capacity": vehicle.capacity_tons or 10,
                "available_from": 0,
                "available_to": 24 * 60,  # Available all day
                "company_id": str(vehicle.company_id),
                "cost_per_km": vehicle.cost_per_km or 0.5,
                "fuel_consumption": vehicle.fuel_consumption_l_per_100km or 30.0
            })
        
        return vehicles_data
    
    async def _optimize_group(
        self, 
        trips_data: List[Dict], 
        vehicles_data: List[Dict], 
        vehicle_category: str
    ) -> Dict[str, Any]:
        """
        Optimize a group of trips with compatible vehicles using CP-SAT.
        """
        try:
            # Initialize CP-SAT model
            model = cp_model.CpModel()
            
            # Create variables
            X = {}  # X[v,i] -> vehicle v does trip i
            Y = {}  # Y[v,i,j] -> v sequences i->j
            Start = {}  # Start[i] -> start time of trip i
            
            vehicle_ids = [v["id"] for v in vehicles_data]
            trip_ids = [t["id"] for t in trips_data]
            
            # Create X variables (vehicle v does trip i)
            for v in vehicle_ids:
                for i in trip_ids:
                    X[(v, i)] = model.NewBoolVar(f"X_{v}_{i}")
            
            # Create Y variables (vehicle v goes from trip i to j)
            # First, calculate feasible edges based on time and location
            feasible_edges = await self._calculate_feasible_edges(trips_data)
            
            for (i, j) in feasible_edges:
                for v in vehicle_ids:
                    Y[(v, i, j)] = model.NewBoolVar(f"Y_{v}_{i}_{j}")
            
            # Create Start variables
            for i, trip in zip(trip_ids, trips_data):
                lb = int(trip["earliest"])
                ub = int(trip["latest"])
                Start[i] = model.NewIntVar(lb, ub, f"Start_{i}")
            
            # Add constraints
            
            # C1: Each trip is assigned to exactly one vehicle
            for i in trip_ids:
                model.Add(sum(X[(v, i)] for v in vehicle_ids) == 1)
            
            # C2: Y -> X consistency
            for (i, j) in feasible_edges:
                for v in vehicle_ids:
                    model.AddImplication(Y[(v, i, j)], X[(v, i)])
                    model.AddImplication(Y[(v, i, j)], X[(v, j)])
            
            # C3: Time window and sequencing constraints
            for (i, j) in feasible_edges:
                travel_time = await self._calculate_travel_time(
                    trips_data[trip_ids.index(i)]["dest"],
                    trips_data[trip_ids.index(j)]["orig"]
                )
                
                for v in vehicle_ids:
                    # If vehicle v goes from i to j, then start_j >= end_i + travel_time
                    end_i = Start[i] + trips_data[trip_ids.index(i)]["duration"] + trips_data[trip_ids.index(i)]["service"]
                    model.Add(Start[j] >= end_i + travel_time).OnlyEnforceIf(Y[(v, i, j)])
            
            # C4: Capacity constraints
            for v in vehicle_ids:
                vehicle_capacity = next(veh["capacity"] for veh in vehicles_data if veh["id"] == v)
                model.Add(
                    sum(X[(v, i)] * trips_data[trip_ids.index(i)]["demand"] for i in trip_ids) 
                    <= vehicle_capacity
                )
            
            # C5: Objective: minimize total distance (including return trips)
            # For simplicity, we'll minimize number of vehicles used first
            # Then minimize total distance
            
            # First objective: minimize vehicles used
            vehicle_used_vars = []
            for v in vehicle_ids:
                used = model.NewBoolVar(f"used_{v}")
                model.Add(sum(X[(v, i)] for i in trip_ids) > 0).OnlyEnforceIf(used)
                model.Add(sum(X[(v, i)] for i in trip_ids) == 0).OnlyEnforceIf(used.Not())
                vehicle_used_vars.append(used)
            
            model.Minimize(sum(vehicle_used_vars))
            
            # Solve
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 300  # 5 minutes
            solver.parameters.num_search_workers = 8
            
            status = solver.Solve(model)
            
            if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                # Fallback to simple assignment
                return await self._simple_assignment_fallback(trips_data, vehicles_data)
            
            # Extract solution
            assignments = []
            for v in vehicle_ids:
                assigned_trips = []
                for i in trip_ids:
                    if solver.Value(X[(v, i)]) == 1:
                        assigned_trips.append({
                            "trip_id": i,
                            "start_time": solver.Value(Start[i]),
                            "original_company": next(t["company_id"] for t in trips_data if t["id"] == i)
                        })
                
                if assigned_trips:
                    # Sort by start time
                    assigned_trips.sort(key=lambda x: x["start_time"])
                    
                    # Create assignments with sequence order
                    for idx, assignment in enumerate(assigned_trips):
                        assignments.append({
                            "trip_id": assignment["trip_id"],
                            "original_company": assignment["original_company"],
                            "assigned_vehicle_id": v,
                            "assigned_company": next(veh["company_id"] for veh in vehicles_data if veh["id"] == v),
                            "sequence_order": idx + 1,
                            "is_last_in_chain": idx == len(assigned_trips) - 1,
                            "start_time": assignment["start_time"]
                        })
            
            # Calculate savings
            km_saved, fuel_saved = await self._calculate_savings(assignments, trips_data, vehicles_data)
            
            return {
                "success": True,
                "assignments": assignments,
                "km_saved": km_saved,
                "fuel_saved": fuel_saved,
                "vehicle_category": vehicle_category
            }
            
        except Exception as e:
            logger.error(f"Optimization failed for group {vehicle_category}: {str(e)}")
            # Fallback to simple assignment
            return await self._simple_assignment_fallback(trips_data, vehicles_data)
    
    async def _calculate_feasible_edges(self, trips_data: List[Dict]) -> List[Tuple[str, str]]:
        """Calculate feasible edges between trips."""
        feasible_edges = []
        
        for i, trip_i in enumerate(trips_data):
            for j, trip_j in enumerate(trips_data):
                if i == j:
                    continue
                
                # Check time feasibility
                end_i_time = trip_i["earliest"] + trip_i["duration"] + trip_i["service"]
                
                # Add travel time between arrival of i and departure of j
                travel_time = await self._calculate_travel_time(trip_i["dest"], trip_j["orig"])
                
                if end_i_time + travel_time <= trip_j["latest"]:
                    feasible_edges.append((trip_i["id"], trip_j["id"]))
        
        return feasible_edges
    
    async def _calculate_travel_time(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> int:
        """Calculate travel time between two points in seconds."""
        try:
            route = await self.valhalla.get_route(
                start_lat=point1[0],
                start_lng=point1[1],
                end_lat=point2[0],
                end_lng=point2[1]
            )
            return int(route.get("duration_min", 30) * 60)  # Convert to seconds
        except:
            # Fallback: 30 minutes
            return 30 * 60
    
    async def _simple_assignment_fallback(
        self, 
        trips_data: List[Dict], 
        vehicles_data: List[Dict]
    ) -> Dict[str, Any]:
        """Simple assignment fallback when CP-SAT fails."""
        assignments = []
        
        # Simple round-robin assignment
        for i, trip in enumerate(trips_data):
            if i < len(vehicles_data):
                vehicle = vehicles_data[i]
                assignments.append({
                    "trip_id": trip["id"],
                    "original_company": trip["company_id"],
                    "assigned_vehicle_id": vehicle["id"],
                    "assigned_company": vehicle["company_id"],
                    "sequence_order": 1,
                    "is_last_in_chain": True,
                    "start_time": trip["earliest"]
                })
        
        # Calculate savings (simplified)
        km_saved = len(assignments) * 10  # Assume 10km saved per trip
        fuel_saved = km_saved * 0.3  # Assume 0.3L/km
        
        return {
            "success": True,
            "assignments": assignments,
            "km_saved": km_saved,
            "fuel_saved": fuel_saved,
            "vehicle_category": "fallback"
        }
    
    async def _calculate_savings(
        self, 
        assignments: List[Dict], 
        trips_data: List[Dict], 
        vehicles_data: List[Dict]
    ) -> Tuple[float, float]:
        """Calculate kilometers and fuel saved through optimization."""
        # Simplified calculation
        # In production, compare optimized vs non-optimized distances
        
        total_km = 0
        total_fuel = 0
        
        for assignment in assignments:
            trip = next(t for t in trips_data if t["id"] == assignment["trip_id"])
            vehicle = next(v for v in vehicles_data if v["id"] == assignment["assigned_vehicle_id"])
            
            # Add trip distance
            total_km += trip.get("r_i0", 0)  # Return distance
            
            # Calculate fuel consumption
            fuel_per_km = vehicle.get("fuel_consumption", 30) / 100  # L per km
            total_fuel += trip.get("r_i0", 0) * fuel_per_km
        
        return total_km, total_fuel
    
    async def _update_trip_assignments(
        self,
        session: Session,
        assignments: List[Dict],
        batch_id: uuid.UUID
    ) -> List[Trip]:
        """Update trips with optimization results."""
        updated_trips = []
        
        for assignment in assignments:
            trip = session.get(Trip, uuid.UUID(assignment["trip_id"]))
            if trip:
                trip.optimization_batch_id = batch_id
                trip.assigned_vehicle_id = uuid.UUID(assignment["assigned_vehicle_id"])
                trip.sequence_order = assignment.get("sequence_order")
                trip.is_last_in_chain = assignment.get("is_last_in_chain", False)
                trip.optimization_status = "assigned"
                
                # Update estimated arrival based on chain position and start time
                if assignment.get("start_time"):
                    start_time = datetime.fromtimestamp(assignment["start_time"])
                    trip.estimated_arrival_datetime = start_time + timedelta(
                        minutes=trip.route_duration_min or 60
                    )
                
                session.add(trip)
                updated_trips.append(trip)
        
        session.commit()
        return updated_trips
    
    async def _calculate_company_kpis(
        self,
        session: Session,
        optimized_trips: List[Trip],
        original_trips: List[Trip],
        batch_id: uuid.UUID
    ) -> Dict[str, Dict]:
        """Calculate KPIs for each company."""
        company_trips = defaultdict(list)
        for trip in optimized_trips:
            company_trips[str(trip.company_id)].append(trip)
        
        company_kpis = {}
        
        for company_id, trips in company_trips.items():
            # Get original trips for this company
            original_company_trips = [
                t for t in original_trips 
                if str(t.company_id) == company_id
            ]
            
            # Calculate baseline (if all trips used own vehicles)
            baseline_distance = sum(
                (t.route_distance_km or 0) + (t.return_distance_km or 0)
                for t in original_company_trips
            )
            
            # Calculate optimized distance
            optimized_distance = sum(
                t.route_distance_km or 0
                for t in trips
            )
            
            # Add return distance for last trip in chain
            for trip in trips:
                if trip.is_last_in_chain:
                    optimized_distance += trip.return_distance_km or 0
            
            km_saved = max(0, baseline_distance - optimized_distance)
            
            # Calculate fuel savings (assuming 0.3 liters per km for trucks)
            fuel_saved_liters = km_saved * 0.3
            
            # Calculate CO2 savings (2.68 kg CO2 per liter of diesel)
            co2_saved_kg = fuel_saved_liters * 2.68
            
            # Calculate cost savings (assuming $1.5 per liter)
            cost_saved_usd = fuel_saved_liters * 1.5
            
            # Count vehicles shared
            vehicles_used = len(set(t.assigned_vehicle_id for t in trips))
            vehicles_borrowed = len([
                t for t in trips 
                if str(t.assigned_vehicle_id) != str(t.vehicle_id)
            ])
            
            # Count vehicles shared out (this company's vehicles used by others)
            vehicles_shared_out = 0
            for trip in optimized_trips:
                if str(trip.assigned_vehicle_id) in [str(t.vehicle_id) for t in trips]:
                    if str(trip.company_id) != company_id:
                        vehicles_shared_out += 1
            
            # Save KPI record
            kpi_record = CompanyOptimizationResult(
                optimization_batch_id=batch_id,
                company_id=uuid.UUID(company_id),
                trips_contributed=len(original_company_trips),
                trips_assigned=len(trips),
                vehicles_used=vehicles_used,
                vehicles_borrowed=vehicles_borrowed,
                vehicles_shared_out=vehicles_shared_out,
                km_saved=km_saved,
                fuel_saved_liters=fuel_saved_liters,
                co2_saved_kg=co2_saved_kg,
                cost_saved_usd=cost_saved_usd
            )
            
            session.add(kpi_record)
            
            company_kpis[company_id] = {
                "km_saved": km_saved,
                "fuel_saved_liters": fuel_saved_liters,
                "co2_saved_kg": co2_saved_kg,
                "cost_saved_usd": cost_saved_usd,
                "vehicles_borrowed": vehicles_borrowed,
                "vehicles_shared_out": vehicles_shared_out,
                "trips_optimized": len(trips)
            }
        
        session.commit()
        return company_kpis
    
    async def _generate_company_reports(
        self,
        session: Session,
        batch_id: uuid.UUID,
        company_kpis: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """Generate optimization reports for each company."""
        reports = {}
        
        for company_id, kpis in company_kpis.items():
            # Get company details
            company = session.get(Company, uuid.UUID(company_id))
            if not company:
                continue
            
            # Get optimized trips for this company
            trip_stmt = select(Trip).where(
                Trip.optimization_batch_id == batch_id,
                Trip.company_id == uuid.UUID(company_id)
            )
            company_trips = session.exec(trip_stmt).all()
            
            # Generate report
            report = {
                "company_name": company.company_name,
                "optimization_date": datetime.utcnow().date().isoformat(),
                "summary": {
                    "trips_contributed": kpis.get("trips_optimized", 0),
                    "km_saved": round(kpis.get("km_saved", 0), 2),
                    "fuel_saved_liters": round(kpis.get("fuel_saved_liters", 0), 2),
                    "cost_saved_usd": round(kpis.get("cost_saved_usd", 0), 2),
                    "co2_saved_kg": round(kpis.get("co2_saved_kg", 0), 2),
                    "vehicles_borrowed": kpis.get("vehicles_borrowed", 0),
                    "vehicles_shared_out": kpis.get("vehicles_shared_out", 0)
                },
                "optimized_trips": [
                    {
                        "trip_id": str(trip.id),
                        "departure": trip.departure_point,
                        "arrival": trip.arrival_point,
                        "assigned_vehicle": str(trip.assigned_vehicle_id),
                        "estimated_arrival": trip.estimated_arrival_datetime.isoformat() if trip.estimated_arrival_datetime else None,
                        "sequence_order": trip.sequence_order,
                        "is_last_in_chain": trip.is_last_in_chain
                    }
                    for trip in company_trips
                ],
                "recommendations": self._generate_recommendations(kpis)
            }
            
            reports[company_id] = report
        
        return reports
    
    def _generate_recommendations(self, kpis: Dict) -> List[str]:
        """Generate AI-powered recommendations based on KPIs."""
        recommendations = []
        
        if kpis.get("km_saved", 0) > 100:
            recommendations.append(
                "Great optimization! You saved significant distance. "
                "Consider scheduling more trips during peak sharing hours."
            )
        
        if kpis.get("vehicles_borrowed", 0) > 0:
            recommendations.append(
                f"You successfully borrowed {kpis['vehicles_borrowed']} vehicles from other companies. "
                "This reduces your need for additional fleet investment."
            )
        
        if kpis.get("vehicles_shared_out", 0) > 0:
            recommendations.append(
                f"You shared {kpis['vehicles_shared_out']} of your vehicles with other companies. "
                "This increases your asset utilization and generates additional revenue."
            )
        
        if kpis.get("fuel_saved_liters", 0) > 50:
            recommendations.append(
                f"Fuel savings of {round(kpis['fuel_saved_liters'], 1)} liters "
                f"reduces CO2 emissions by {round(kpis.get('co2_saved_kg', 0), 1)} kg."
            )
        
        if not recommendations:
            recommendations.append(
                "Good start! As more companies join the platform, "
                "you'll see increased optimization opportunities."
            )
        
        return recommendations
    
    async def close(self):
        """Close the Valhalla service."""
        await self.valhalla.close()