from typing import List, Dict, Any
from app.models import OptimizationRequest, ValidationResult, TripCreate, VehicleCreate


class ValidationService:
    def validate_request(self, request: OptimizationRequest) -> ValidationResult:
        errors = []
        warnings = []
        
        # Check for empty data
        if not request.trips:
            errors.append("No trips provided")
        if not request.vehicles:
            errors.append("No vehicles provided")
            
        if errors:
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        # Validate individual trips
        trip_ids = set()
        for trip in request.trips:
            trip_errors = self._validate_trip(trip)
            errors.extend(trip_errors)
            if trip.id in trip_ids:
                errors.append(f"Duplicate trip ID: {trip.id}")
            trip_ids.add(trip.id)
        
        # Validate individual vehicles
        vehicle_ids = set()
        for vehicle in request.vehicles:
            vehicle_errors = self._validate_vehicle(vehicle)
            errors.extend(vehicle_errors)
            if vehicle.id in vehicle_ids:
                errors.append(f"Duplicate vehicle ID: {vehicle.id}")
            vehicle_ids.add(vehicle.id)
        
        # Validate capacity constraints
        total_demand = sum(trip.demand for trip in request.trips)
        total_capacity = sum(vehicle.capacity for vehicle in request.vehicles)
        
        if total_demand > total_capacity:
            errors.append(
                f"Total demand ({total_demand}) exceeds total vehicle capacity ({total_capacity})"
            )
        
        # Check time window feasibility
        for trip in request.trips:
            if trip.earliest > trip.latest:
                errors.append(f"Trip {trip.id}: earliest time ({trip.earliest}) > latest time ({trip.latest})")
        
        for vehicle in request.vehicles:
            if vehicle.available_from > vehicle.available_to:
                errors.append(f"Vehicle {vehicle.id}: available_from ({vehicle.available_from}) > available_to ({vehicle.available_to})")
        
        # Check if any vehicle can serve the time windows
        earliest_trip = min(trip.earliest for trip in request.trips)
        latest_trip = max(trip.latest for trip in request.trips)
        
        suitable_vehicles = [
            v for v in request.vehicles 
            if v.available_from <= earliest_trip and v.available_to >= latest_trip
        ]
        
        if not suitable_vehicles:
            warnings.append(
                "No vehicles have availability windows that cover all trip time windows"
            )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    def _validate_trip(self, trip: TripCreate) -> List[str]:
        errors = []
        
        if trip.demand <= 0:
            errors.append(f"Trip {trip.id}: demand must be positive")
        
        if trip.duration <= 0:
            errors.append(f"Trip {trip.id}: duration must be positive")
        
        if trip.service < 0:
            errors.append(f"Trip {trip.id}: service time cannot be negative")
        
        if trip.r_i0 < 0:
            errors.append(f"Trip {trip.id}: return time cannot be negative")
        
        if trip.earliest < 0 or trip.latest > 1440:  # 24 hours in minutes
            errors.append(f"Trip {trip.id}: time windows must be between 0 and 1440 minutes")
        
        return errors
    
    def _validate_vehicle(self, vehicle: VehicleCreate) -> List[str]:
        errors = []
        
        if vehicle.capacity <= 0:
            errors.append(f"Vehicle {vehicle.id}: capacity must be positive")
        
        if vehicle.available_from < 0 or vehicle.available_to > 1440:
            errors.append(f"Vehicle {vehicle.id}: availability must be between 0 and 1440 minutes")
        
        if vehicle.depot_loc < 0:
            errors.append(f"Vehicle {vehicle.id}: depot location must be non-negative")
        
        return errors