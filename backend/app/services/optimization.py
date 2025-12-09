import uuid
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from ortools.sat.python import cp_model

from app.models.optimization_full_models import (
    OptimizationResult,
    AssignmentResult,
    Trip,
    Vehicle,
    Config,
    JobStatus,
    OptimizationGroup
)
from app.core.db import engine
from sqlmodel import Session, select


class OptimizationService:
    def __init__(self):
        self.model = None
        self.solver = None
        
    def solve_optimization(self, request_data: Dict[str, Any]) -> OptimizationResult:
        """
        Main optimization method that orchestrates the CP-SAT solving process.
        """
        try:
            # Extract data from request
            company_id = request_data["company_id"]
            optimization_group_id = request_data["optimization_group_id"]
            config = request_data.get("config", {})
            
            # Get trips and vehicles for this optimization group
            trips_data, vehicles_data = self._get_optimization_data(
                company_id, optimization_group_id
            )
            
            if not trips_data or not vehicles_data:
                return OptimizationResult(
                    job_id=uuid.uuid4(),  # Will be replaced by actual job ID
                    status=JobStatus.INFEASIBLE,
                    diagnostics=["No trips or vehicles found for optimization group"]
                )
            
            # Build and solve the CP-SAT model
            solution = self._build_and_solve_cpsat_model(
                trips_data, vehicles_data, config
            )
            
            return solution
            
        except Exception as e:
            return OptimizationResult(
                job_id=uuid.uuid4(),
                status=JobStatus.FAILED,
                diagnostics=[f"Optimization failed: {str(e)}"]
            )
    
    def _get_optimization_data(self, company_id: uuid.UUID, optimization_group_id: uuid.UUID) -> Tuple[List[Dict], List[Dict]]:
        """
        Get trips and vehicles data for the optimization group.
        """
        with Session(engine) as session:
            # Get optimization group
            optimization_group = session.get(OptimizationGroup, optimization_group_id)
            if not optimization_group:
                return [], []
            
            # Get trips for this company and product categories compatible with the vehicle category
            product_category_ids = session.exec(
                select(ProductCategory.id)
                .where(ProductCategory.sector == optimization_group.sector)
            ).all()
            
            trip_stmt = (
                select(Trip)
                .where(Trip.company_id == company_id)
                .where(Trip.product_category_id.in_(product_category_ids))
            )
            trips = session.exec(trip_stmt).all()
            
            # Get vehicles for this company and the specific vehicle category
            vehicle_stmt = (
                select(Vehicle)
                .where(Vehicle.company_id == company_id)
                .where(Vehicle.category_id == optimization_group.vehicle_category_id)
                .where(Vehicle.state == "actif")
                .where(Vehicle.current_status == "disponible")
            )
            vehicles = session.exec(vehicle_stmt).all()
            
            # Convert to optimization format
            trips_data = []
            for trip in trips:
                trips_data.append({
                    "id": str(trip.id),
                    "reference": trip.reference,
                    "orig": trip.start_point,
                    "dest": trip.end_point,
                    "earliest": trip.earliest_start,
                    "latest": trip.latest_start,
                    "duration": trip.duration or self._calculate_duration(trip),
                    "service": trip.service_time,
                    "demand": trip.demand,
                    "r_i0": trip.return_to_depot_time or self._calculate_return_time(trip),
                    "company_id": str(trip.company_id)
                })
            
            vehicles_data = []
            for vehicle in vehicles:
                vehicles_data.append({
                    "id": vehicle.id,
                    "depot": vehicle.depot_location,
                    "capacity": vehicle.capacity,
                    "available_from": 0,  # Could be customized per vehicle
                    "available_to": 24 * 60,  # Full day
                    "company_id": str(vehicle.company_id)
                })
            
            return trips_data, vehicles_data
    
    def _calculate_duration(self, trip: Trip) -> int:
        """
        Calculate trip duration based on distance and average speed.
        In production, this would use a routing service.
        """
        # Placeholder - in production, use actual routing
        return 60  # Default 60 minutes
    
    def _calculate_return_time(self, trip: Trip) -> int:
        """
        Calculate return time to depot from destination.
        """
        # Placeholder - in production, use actual routing
        return 30  # Default 30 minutes
    
    def _build_and_solve_cpsat_model(self, trips: List[Dict], vehicles: List[Dict], config: Dict) -> OptimizationResult:
        """
        Build and solve the CP-SAT model based on the provided data.
        """
        # Convert trips to dictionary format for easier access
        trips_dict = {trip["id"]: trip for trip in trips}
        vehicles_dict = {vehicle["id"]: vehicle for vehicle in vehicles}

        trip_ids = list(trips_dict.keys())
        vehicle_ids = list(vehicles_dict.keys())

        if not trip_ids or not vehicle_ids:
            return OptimizationResult(
                job_id=str(uuid.uuid4()),
                status=JobStatus.INFEASIBLE,
                diagnostics=["No trips or vehicles available for optimization"]
            )

        # Preprocessing: calculate time windows and feasible edges
        for trip_id, trip in trips_dict.items():
            trip["earliest_int"] = int(trip["earliest"])
            trip["latest_start_int"] = int(max(trip["earliest_int"], int(trip["latest"]) - int(trip["duration"])))

        # Calculate feasible edges (compatible trip sequences)
        feasible_edges = self._calculate_feasible_edges(trips_dict)

        # Build CP-SAT model
        model = cp_model.CpModel()

        # Create variables
        X, Y, IsLast, L, Start = self._create_variables(
            model, trip_ids, vehicle_ids, feasible_edges, trips_dict
        )

        # Add constraints
        self._add_constraints(
            model, X, Y, IsLast, L, Start, 
            trip_ids, vehicle_ids, feasible_edges, 
            trips_dict, vehicles_dict
        )

        # Solve with lexicographic objectives
        solution = self._solve_with_lexicographic_objectives(
            model, X, Y, IsLast, L, Start,
            trip_ids, vehicle_ids, feasible_edges,
            trips_dict, vehicles_dict, config
        )

        return solution
    
    def _calculate_feasible_edges(self, trips_dict: Dict) -> List[Tuple[str, str]]:
        """
        Calculate feasible edges between trips based on location compatibility and time windows.
        """
        feasible_edges = []
        
        # In production, this would use actual routing and distance calculations
        # For now, we'll use a simplified approach
        for i, trip_i in trips_dict.items():
            for j, trip_j in trips_dict.items():
                if i == j:
                    continue
                
                # Check if destination of i matches origin of j
                # In production, this would use geocoding and proximity checks
                if trip_i["dest"] == trip_j["orig"]:
                    # Check time window feasibility
                    earliest_finish_i = trip_i["earliest_int"] + trip_i["duration"] + trip_i["service"]
                    travel_time = 15  # Default travel time between locations
                    
                    if earliest_finish_i + travel_time <= trip_j["latest_start_int"]:
                        feasible_edges.append((i, j))
        
        return feasible_edges
    
    def _create_variables(self, model, trip_ids, vehicle_ids, feasible_edges, trips_dict):
        """
        Create CP-SAT variables.
        """
        X = {}  # X[v,i] -> vehicle v does trip i
        Y = {}  # Y[v,i,j] -> v sequences i->j
        IsLast = {}  # IsLast[v,i] -> i is last trip of v
        L = {}  # L[v] -> v makes a return trip
        Start = {}  # Start[i] -> start time of trip i
        
        # Create variables
        for v in vehicle_ids:
            for i in trip_ids:
                X[(v, i)] = model.NewBoolVar(f"X_{v}_{i}")
                IsLast[(v, i)] = model.NewBoolVar(f"IsLast_{v}_{i}")
            L[v] = model.NewBoolVar(f"L_{v}")
        
        for (i, j) in feasible_edges:
            for v in vehicle_ids:
                Y[(v, i, j)] = model.NewBoolVar(f"Y_{v}_{i}_{j}")
        
        for i in trip_ids:
            lb = trips_dict[i]["earliest_int"]
            ub = trips_dict[i]["latest_start_int"]
            if ub < lb:
                ub = lb  # Handle impossible time windows
            Start[i] = model.NewIntVar(lb, ub, f"Start_{i}")
        
        return X, Y, IsLast, L, Start
    
    def _add_constraints(self, model, X, Y, IsLast, L, Start, 
                        trip_ids, vehicle_ids, feasible_edges, 
                        trips_dict, vehicles_dict):
        """
        Add all constraints to the CP-SAT model.
        """
        # C1: Each trip is assigned to exactly one vehicle
        for i in trip_ids:
            model.Add(sum(X[(v, i)] for v in vehicle_ids) == 1)
        
        # C2, C3: Y -> X consistency and sequencing constraints
        for (i, j) in feasible_edges:
            travel_time = 15  # Default travel time
            for v in vehicle_ids:
                model.AddImplication(Y[(v, i, j)], X[(v, i)])
                model.AddImplication(Y[(v, i, j)], X[(v, j)])
                # C8: Sequencing constraint
                model.Add(Start[j] >= Start[i] + 
                         trips_dict[i]["duration"] + 
                         trips_dict[i]["service"] + 
                         travel_time).OnlyEnforceIf(Y[(v, i, j)])
        
        # C4: IsLast and L variable relationships
        for v in vehicle_ids:
            for i in trip_ids:
                # Find outgoing edges from i
                outs = [Y[(v, a, b)] for (a, b) in feasible_edges if a == i]
                if outs:
                    model.Add(sum(outs) + IsLast[(v, i)] == X[(v, i)])
                else:
                    model.Add(IsLast[(v, i)] == X[(v, i)])
            
            # L[v] is 1 if any IsLast[v,i] is 1
            islasts = [IsLast[(v, i)] for i in trip_ids]
            model.Add(sum(islasts) >= L[v])
            model.Add(sum(islasts) <= len(trip_ids) * L[v])
        
        # C5: Capacity constraints
        for v in vehicle_ids:
            model.Add(sum(X[(v, i)] * trips_dict[i]["demand"] for i in trip_ids) <= 
                     vehicles_dict[v]["capacity"])
        
        # C7: Time window constraints (already handled by Start variable bounds)
        
        # C8: Degree constraints (each trip has at most one incoming and one outgoing edge per vehicle)
        for v in vehicle_ids:
            for i in trip_ids:
                outs = [Y[(v, a, b)] for (a, b) in feasible_edges if a == i]
                ins = [Y[(v, a, b)] for (a, b) in feasible_edges if b == i]
                if outs:
                    model.Add(sum(outs) <= 1)
                if ins:
                    model.Add(sum(ins) <= 1)
        
        # C9: Return distance constraints (simplified)
        for v in vehicle_ids:
            # Conservative approach: sum of return distances <= sum of initial return allowances
            return_dist_terms = []
            for i in trip_ids:
                # Simplified return distance calculation
                return_dist = 20  # Default return distance
                return_dist_terms.append(IsLast[(v, i)] * return_dist)
            
            if return_dist_terms:
                return_dist_total = sum(return_dist_terms)
                rhs = sum(X[(v, i)] * trips_dict[i]["r_i0"] for i in trip_ids)
                model.Add(return_dist_total <= rhs)
    
    def _solve_with_lexicographic_objectives(self, model, X, Y, IsLast, L, Start,
                                           trip_ids, vehicle_ids, feasible_edges,
                                           trips_dict, vehicles_dict, config):
        """
        Solve with lexicographic objectives: first minimize vehicles used, then minimize return distances.
        """
        # First objective: minimize number of vehicles used (sum of L[v])
        sumL = sum(L[v] for v in vehicle_ids)
        model.Minimize(sumL)
        
        # Configure solver
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = config.get("timeout_seconds", 300)
        solver.parameters.num_search_workers = config.get("num_workers", 8)
        solver.parameters.log_search_progress = True
        
        # Solve first objective
        status = solver.Solve(model)
        
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return OptimizationResult(
                job_id=uuid.uuid4(),
                status=JobStatus.INFEASIBLE,
                diagnostics=["No feasible solution found for primary objective"]
            )
        
        bestL = int(solver.ObjectiveValue())
        
        # Second objective: minimize total return distance while keeping bestL
        # For CP-SAT, we need to create a new model with the additional constraint
        model2 = cp_model.CpModel()
        
        # Recreate variables and constraints (simplified approach)
        # In production, you might want to use a more efficient approach
        X2, Y2, IsLast2, L2, Start2 = self._create_variables(
            model2, trip_ids, vehicle_ids, feasible_edges, trips_dict
        )
        
        self._add_constraints(
            model2, X2, Y2, IsLast2, L2, Start2,
            trip_ids, vehicle_ids, feasible_edges,
            trips_dict, vehicles_dict
        )
        
        # Add constraint to maintain the first objective value
        model2.Add(sum(L2[v] for v in vehicle_ids) <= bestL)
        
        # Second objective: minimize total return distance
        total_return_dist = 0
        for v in vehicle_ids:
            for i in trip_ids:
                return_dist = 20  # Default return distance
                total_return_dist += IsLast2[(v, i)] * return_dist
        
        model2.Minimize(total_return_dist)
        
        # Solve second objective
        solver2 = cp_model.CpSolver()
        solver2.parameters.max_time_in_seconds = config.get("timeout_seconds", 300) - solver.WallTime()
        solver2.parameters.num_search_workers = config.get("num_workers", 8)
        
        status2 = solver2.Solve(model2)
        
        if status2 not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            # Use first solution if second fails
            return self._extract_solution(
                solver, X, Y, IsLast, Start,
                trip_ids, vehicle_ids, feasible_edges,
                trips_dict, vehicles_dict, bestL, config
            )
        else:
            return self._extract_solution(
                solver2, X2, Y2, IsLast2, Start2,
                trip_ids, vehicle_ids, feasible_edges,
                trips_dict, vehicles_dict, bestL, config
            )
    
    def _extract_solution(self, solver, X, Y, IsLast, Start,
                         trip_ids, vehicle_ids, feasible_edges,
                         trips_dict, vehicles_dict, vehicles_used, config):
        """
        Extract solution from solver and format as OptimizationResult.
        """
        if solver.Status() not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return OptimizationResult(
                job_id=uuid.uuid4(),
                status=JobStatus.INFEASIBLE,
                diagnostics=["No feasible solution could be extracted"]
            )
        
        # Extract assignments
        assignments = []
        vehicle_chains = defaultdict(list)
        
        for v in vehicle_ids:
            # Find trips assigned to this vehicle
            assigned_trips = []
            for i in trip_ids:
                if solver.Value(X[(v, i)]) == 1:
                    assigned_trips.append(i)
            
            if not assigned_trips:
                continue
            
            # Build chains using Y variables
            next_map = {}
            for (i, j) in feasible_edges:
                if solver.Value(Y[(v, i, j)]) == 1:
                    next_map[i] = j
            
            # Find chain starts (trips with no incoming edge)
            starts = [i for i in assigned_trips if i not in next_map.values()]
            
            chains = []
            for start in starts:
                chain = [start]
                current = start
                while current in next_map:
                    current = next_map[current]
                    chain.append(current)
                chains.append(chain)
            
            # Convert chains to assignment format
            for chain in chains:
                trip_sequence = []
                start_times = []
                end_times = []
                is_last_flags = []
                
                for i in chain:
                    trip_sequence.append(i)
                    start_time = solver.Value(Start[i])
                    start_times.append(start_time)
                    end_times.append(start_time + trips_dict[i]["duration"])
                    is_last = solver.Value(IsLast[(v, i)]) == 1
                    is_last_flags.append(is_last)
                
                assignment = AssignmentResult(
                    vehicle_id=v,
                    trip_sequence=trip_sequence,
                    start_times=start_times,
                    end_times=end_times,
                    is_last=is_last_flags
                )
                assignments.append(assignment)
        
        # Calculate metrics
        total_return_distance = 0
        for v in vehicle_ids:
            for i in trip_ids:
                if solver.Value(IsLast[(v, i)]) == 1:
                    total_return_distance += 20  # Simplified
        
        metrics = {
            "solve_time_s": solver.WallTime(),
            "num_assignments": len(assignments),
            "num_vehicles_used": vehicles_used,
            "total_return_distance": total_return_distance,
            "solver_status": solver.StatusName()
        }
        
        return OptimizationResult(
            job_id=uuid.uuid4(),  # Will be replaced by actual job ID
            status=JobStatus.COMPLETED,
            objective=float(vehicles_used),  # Primary objective value
            metrics=metrics,
            assignments=assignments,
            diagnostics=[]
        )