"""
Constraint Programming (CP-SAT) based trip optimization service
Uses OR-Tools CP-SAT solver instead of MILP for better performance
"""
import math
import uuid
from collections import defaultdict
from datetime import datetime
from typing import DefaultDict

from ortools.sat.python import cp_model
from sqlmodel import Session

from app.models.company_models import Vehicle, VehicleCategory
from app.models.trip_models import CargoCategory, Trip
from app.crud import (
    get_trips_for_date,
    get_available_vehicles_by_category,
    create_optimization_batch,
    update_optimization_batch
)

# ============= DISTANCE CALCULATION =============
def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two lat/lng points"""
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def calculate_trip_distance(trip: Trip) -> float:
    """Calculate trip distance if coordinates are available"""
    departure_lat = trip.departure_lat
    departure_lng = trip.departure_lng
    arrival_lat = trip.arrival_lat
    arrival_lng = trip.arrival_lng

    if (
        departure_lat is None
        or departure_lng is None
        or arrival_lat is None
        or arrival_lng is None
    ):
        return 0.0

    return haversine_distance(
        departure_lat,
        departure_lng,
        arrival_lat,
        arrival_lng
    )

# ============= TRIP GROUPING =============
def group_trips_by_compatibility(
    trips: list[Trip],
) -> dict[VehicleCategory, list[Trip]]:
    """
    Group trips by vehicle category compatibility
    Key: vehicle_category, Value: list of compatible trips
    """
    groups: DefaultDict[VehicleCategory, list[Trip]] = defaultdict(list)
    
    for trip in trips:
        # Map cargo category to compatible vehicle categories
        # This is simplified - expand based on your Liste 01 & 02 mappings
        vehicle_category = get_compatible_vehicle_category(trip.cargo_category)
        groups[vehicle_category].append(trip)
    
    return dict(groups)

def get_compatible_vehicle_category(
    cargo_category: CargoCategory | str,
) -> VehicleCategory:
    """
    Map cargo category to vehicle category
    Simplified version - expand based on your full mappings
    """
    if isinstance(cargo_category, str):
        try:
            cargo_enum = CargoCategory(cargo_category)
        except ValueError:
            return VehicleCategory.IN1
    else:
        cargo_enum = cargo_category

    mapping: dict[CargoCategory, VehicleCategory] = {
        # Agroalimentaire cargo -> Agroalimentaire vehicles
        CargoCategory.A01: VehicleCategory.AG1,
        CargoCategory.A02: VehicleCategory.AG2,
        CargoCategory.A03: VehicleCategory.AG5,
        
        # Construction cargo -> Construction vehicles
        CargoCategory.B01: VehicleCategory.BT1,
        CargoCategory.B02: VehicleCategory.BT4,
        
        # Default mapping for other categories can be expanded here
    }
    return mapping.get(cargo_enum, VehicleCategory.IN1)

# ============= CP-SAT SOLVER =============
class TripOptimizationSolver:
    """
    CP-SAT based solver for trip chaining optimization
    Objective: Minimize number of empty returns by maximizing trip chaining
    """
    
    def __init__(self, trips: list[Trip], vehicles: list[Vehicle]):
        self.trips = trips
        self.vehicles = vehicles
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        
        # Decision variables
        self.x: dict[tuple[int, int], cp_model.IntVar] = {}  # x[v,i] = 1 if vehicle v does trip i
        self.y: dict[tuple[int, int, int], cp_model.IntVar] = {}  # y[v,i,j] = 1 if vehicle v chains trip i->j
        self.l: dict[int, cp_model.IntVar] = {}  # l[v] = 1 if vehicle v returns empty
        
        # Time variables (in minutes since midnight)
        self.t_start: dict[int, cp_model.IntVar] = {}  # Start time of trip i
        self.t_end: dict[int, cp_model.IntVar] = {}    # End time of trip i
        
    def build_model(self):
        """Build the CP-SAT model"""
        num_trips = len(self.trips)
        num_vehicles = len(self.vehicles)
        
        # Create decision variables
        for v_idx, vehicle in enumerate(self.vehicles):
            self.l[v_idx] = self.model.NewBoolVar(f'return_{v_idx}')
            
            for i_idx, trip_i in enumerate(self.trips):
                self.x[(v_idx, i_idx)] = self.model.NewBoolVar(f'x_{v_idx}_{i_idx}')
                
                # Time windows (in minutes)
                min_start = int(trip_i.departure_datetime.hour * 60 + trip_i.departure_datetime.minute)
                max_start = int(trip_i.arrival_datetime_planned.hour * 60 + trip_i.arrival_datetime_planned.minute)
                
                self.t_start[i_idx] = self.model.NewIntVar(min_start, max_start, f't_start_{i_idx}')
                self.t_end[i_idx] = self.model.NewIntVar(min_start, max_start + 240, f't_end_{i_idx}')  # +4h buffer
                
                # Chaining variables
                for j_idx, trip_j in enumerate(self.trips):
                    if i_idx != j_idx:
                        self.y[(v_idx, i_idx, j_idx)] = self.model.NewBoolVar(f'y_{v_idx}_{i_idx}_{j_idx}')
        
        # CONSTRAINT 1: Each trip assigned to exactly one vehicle
        for i_idx in range(num_trips):
            self.model.Add(sum(self.x[(v, i_idx)] for v in range(num_vehicles)) == 1)
        
        # CONSTRAINT 2: Chaining is only possible if both trips assigned to same vehicle
        for v_idx in range(num_vehicles):
            for i_idx in range(num_trips):
                for j_idx in range(num_trips):
                    if i_idx != j_idx:
                        # y[v,i,j] <= x[v,i]
                        self.model.Add(self.y[(v_idx, i_idx, j_idx)] <= self.x[(v_idx, i_idx)])
                        # y[v,i,j] <= x[v,j]
                        self.model.Add(self.y[(v_idx, i_idx, j_idx)] <= self.x[(v_idx, j_idx)])
        
        # CONSTRAINT 3: Arrival point = Departure point for chained trips
        for v_idx in range(num_vehicles):
            for i_idx in range(num_trips):
                for j_idx in range(num_trips):
                    if i_idx != j_idx:
                        trip_i = self.trips[i_idx]
                        trip_j = self.trips[j_idx]
                        
                        # Geographic constraint: arrival of i must match departure of j
                        if not self._are_points_compatible(trip_i, trip_j):
                            self.model.Add(self.y[(v_idx, i_idx, j_idx)] == 0)
        
        # CONSTRAINT 4: Capacity constraint
        for v_idx, vehicle in enumerate(self.vehicles):
            for i_idx, trip in enumerate(self.trips):
                # If trip assigned, weight must not exceed capacity
                capacity_kg = vehicle.capacity_tons * 1000 if vehicle.capacity_tons else float('inf')
                if trip.cargo_weight_kg > capacity_kg:
                    self.model.Add(self.x[(v_idx, i_idx)] == 0)
        
        # CONSTRAINT 5: Temporal sequencing
        for v_idx in range(num_vehicles):
            for i_idx in range(num_trips):
                trip_i = self.trips[i_idx]
                duration_i = self._estimate_duration(trip_i)
                
                # End time = Start time + Duration
                self.model.Add(self.t_end[i_idx] == self.t_start[i_idx] + duration_i).OnlyEnforceIf(
                    self.x[(v_idx, i_idx)]
                )
                
                for j_idx in range(num_trips):
                    if i_idx != j_idx:
                        trip_j = self.trips[j_idx]
                        travel_time = self._estimate_travel_time(trip_i, trip_j)
                        
                        # If chained: start_j >= end_i + travel_time
                        self.model.Add(
                            self.t_start[j_idx] >= self.t_end[i_idx] + travel_time
                        ).OnlyEnforceIf(self.y[(v_idx, i_idx, j_idx)])
        
        # CONSTRAINT 6: Return variable logic
        for v_idx in range(num_vehicles):
            trips_done = sum(self.x[(v_idx, i)] for i in range(num_trips))
            chains_made = sum(self.y[(v_idx, i, j)] for i in range(num_trips) for j in range(num_trips) if i != j)
            
            # If trips_done > chains_made, then vehicle returns empty
            self.model.Add(self.l[v_idx] >= trips_done - chains_made)
            self.model.Add(self.l[v_idx] <= trips_done)
        
        # OBJECTIVE: Minimize empty returns
        self.model.Minimize(sum(self.l[v] for v in range(num_vehicles)))
    
    def _are_points_compatible(self, trip_i: Trip, trip_j: Trip) -> bool:
        """Check if arrival of trip_i matches departure of trip_j"""
        arrival_lat = trip_i.arrival_lat
        arrival_lng = trip_i.arrival_lng
        departure_lat = trip_j.departure_lat
        departure_lng = trip_j.departure_lng

        if (
            arrival_lat is None
            or arrival_lng is None
            or departure_lat is None
            or departure_lng is None
        ):
            return False

        # Allow 5km tolerance for matching
        distance = haversine_distance(
            arrival_lat,
            arrival_lng,
            departure_lat,
            departure_lng
        )
        return distance < 5.0
    
    def _estimate_duration(self, trip: Trip) -> int:
        """Estimate trip duration in minutes"""
        if trip.duration_minutes:
            return trip.duration_minutes
        
        # Rough estimate: 1 hour per 60km
        distance = calculate_trip_distance(trip)
        return int((distance / 60) * 60) if distance > 0 else 60
    
    def _estimate_travel_time(self, trip_i: Trip, trip_j: Trip) -> int:
        """Estimate travel time from arrival of i to departure of j"""
        arrival_lat = trip_i.arrival_lat
        arrival_lng = trip_i.arrival_lng
        departure_lat = trip_j.departure_lat
        departure_lng = trip_j.departure_lng

        if (
            arrival_lat is None
            or arrival_lng is None
            or departure_lat is None
            or departure_lng is None
        ):
            return 30  # Default 30 min

        distance = haversine_distance(
            arrival_lat,
            arrival_lng,
            departure_lat,
            departure_lng
        )
        return int((distance / 60) * 60) + 15  # Include 15 min service time
    
    def solve(self, time_limit_seconds: int = 300) -> dict:
        """
        Solve the optimization problem
        Returns: {
            'status': str,
            'objective_value': int,
            'assignments': list of (vehicle_idx, trip_idx),
            'chains': list of (vehicle_idx, trip_i_idx, trip_j_idx),
            'solve_time': float
        }
        """
        self.solver.parameters.max_time_in_seconds = time_limit_seconds
        
        status = self.solver.Solve(self.model)
        
        result = {
            'status': self._get_status_name(status),
            'objective_value': self.solver.ObjectiveValue() if status in [cp_model.OPTIMAL, cp_model.FEASIBLE] else None,
            'assignments': [],
            'chains': [],
            'returns': [],
            'solve_time': self.solver.WallTime()
        }
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            # Extract assignments
            for (v_idx, i_idx), var in self.x.items():
                if self.solver.Value(var) == 1:
                    result['assignments'].append((v_idx, i_idx))
            
            # Extract chains
            for (v_idx, i_idx, j_idx), var in self.y.items():
                if self.solver.Value(var) == 1:
                    result['chains'].append((v_idx, i_idx, j_idx))
            
            # Extract returns
            for v_idx, var in self.l.items():
                if self.solver.Value(var) == 1:
                    result['returns'].append(v_idx)
        
        return result
    
    def _get_status_name(self, status: int) -> str:
        """Convert status code to readable name"""
        status_map = {
            cp_model.OPTIMAL: 'OPTIMAL',
            cp_model.FEASIBLE: 'FEASIBLE',
            cp_model.INFEASIBLE: 'INFEASIBLE',
            cp_model.MODEL_INVALID: 'MODEL_INVALID',
            cp_model.UNKNOWN: 'UNKNOWN'
        }
        return status_map.get(status, 'UNKNOWN')

# ============= SERVICE FUNCTIONS =============
def optimize_trips_for_date(
    *,
    session: Session,
    target_date: datetime
) -> dict:
    """
    Main optimization service: orchestrates trip grouping and solving
    
    Request Lifecycle:
    1. Fetch all planned trips for the date
    2. Group trips by vehicle category compatibility
    3. For each group, fetch available vehicles
    4. Run CP-SAT solver
    5. Update trips with optimization results
    6. Return metrics
    """
    # Step 1: Fetch trips
    trips = get_trips_for_date(session=session, target_date=target_date)
    
    if not trips:
        return {'status': 'NO_TRIPS', 'message': 'No trips found for the date'}
    
    # Create optimization batch
    batch = create_optimization_batch(session=session, batch_date=target_date)
    
    # Step 2: Group by category
    trip_groups = group_trips_by_compatibility(trips)
    
    total_km_saved = 0.0
    all_results = []
    
    # Step 3 & 4: Solve each group
    for vehicle_category, group_trips in trip_groups.items():
        vehicles = get_available_vehicles_by_category(
            session=session,
            category=vehicle_category,
            date=target_date
        )
        
        if not vehicles:
            continue
        
        # Run solver
        solver = TripOptimizationSolver(trips=group_trips, vehicles=vehicles)
        solver.build_model()
        result = solver.solve(time_limit_seconds=300)
        
        all_results.append(result)
        
        # Step 5: Update trips with results
        if result['status'] in ['OPTIMAL', 'FEASIBLE']:
            _apply_optimization_results(
                session=session,
                trips=group_trips,
                vehicles=vehicles,
                result=result,
                batch_id=batch.id
            )
            
            # Calculate savings
            km_saved = _calculate_km_saved(group_trips, result)
            total_km_saved += km_saved
    
    # Step 6: Update batch and return
    fuel_saved = total_km_saved * 0.3  # Assume 0.3L per km
    
    update_optimization_batch(
        session=session,
        batch_id=batch.id,
        status='completed',
        total_trips=len(trips),
        km_saved=total_km_saved,
        fuel_saved_liters=fuel_saved,
        vehicles_used=len(set(v for v, _ in all_results[0]['assignments'])) if all_results else 0,
        completed_at=datetime.utcnow()
    )
    
    return {
        'status': 'SUCCESS',
        'batch_id': str(batch.id),
        'total_trips': len(trips),
        'km_saved': total_km_saved,
        'fuel_saved_liters': fuel_saved,
        'results': all_results
    }

def _apply_optimization_results(
    session: Session,
    trips: list[Trip],
    vehicles: list[Vehicle],
    result: dict,
    batch_id: uuid.UUID
):
    """Apply solver results to database"""
    for v_idx, i_idx in result['assignments']:
        trip = trips[i_idx]
        vehicle = vehicles[v_idx]
        
        trip.optimization_batch_id = batch_id
        trip.assigned_vehicle_id = vehicle.id
        session.add(trip)
    
    # Mark last trips in chains
    chained_trips = set()
    for v_idx, i_idx, j_idx in result['chains']:
        chained_trips.add(i_idx)
    
    for v_idx, i_idx in result['assignments']:
        if i_idx not in chained_trips:
            trips[i_idx].is_last_in_chain = True
    
    session.commit()

def _calculate_km_saved(trips: list[Trip], result: dict) -> float:
    """Calculate total km saved by chaining"""
    # Initial return distances
    initial_return_km = sum(trip.return_distance_km or 0 for trip in trips)
    
    # After optimization: only vehicles that return
    optimized_returns = len(result['returns'])
    avg_return_km = initial_return_km / len(trips) if trips else 0
    optimized_return_km = optimized_returns * avg_return_km
    
    return max(0, initial_return_km - optimized_return_km)