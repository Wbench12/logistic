import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import uuid
import asyncio
from sqlmodel import Session, select
import tempfile
import os

from app.models.trip_models import Trip, TripCreate, MapMarker
from app.models.company_models import Company, Vehicle
from app.services.valhalla_service import ValhallaService
import logging
logger = logging.getLogger(__name__)

class TripUploadService:
    def __init__(self, valhalla_service: ValhallaService):
        self.valhalla = valhalla_service
        
    async def process_upload_file(
        self,
        session: Session,
        company_id: uuid.UUID,
        file_path: str,
        file_type: str = "csv"
    ) -> Dict[str, Any]:
        """Process uploaded trip planning file."""
        try:
            # Read file
            df = self._read_file(file_path, file_type)
            
            # Validate required columns
            self._validate_columns(df)
            
            # Process each trip
            trips_created = []
            failed_trips = []
            
            for _, row in df.iterrows():
                try:
                    trip_data = await self._process_trip_row(
                        session=session,
                        company_id=company_id,
                        row=row
                    )
                    trips_created.append(trip_data)
                except Exception as e:
                    failed_trips.append({
                        'trip_id': row.get('trip_id', 'unknown'),
                        'error': str(e)
                    })
            
            # Generate TTR matrix for all successful trips
            ttr_matrix = None
            if trips_created:
                ttr_matrix = await self._generate_ttr_matrix(trips_created)
            
            # Create summary
            summary = {
                'total_rows': len(df),
                'successful': len(trips_created),
                'failed': len(failed_trips),
                'failed_details': failed_trips
            }
            
            logger.info(f"Upload processed: {summary}")
            
            return {
                'success': True,
                'summary': summary,
                'trips_created': trips_created,
                'ttr_matrix_available': ttr_matrix is not None,
                'ttr_matrix_size': len(ttr_matrix) if ttr_matrix else 0
            }
            
        except Exception as e:
            logger.error(f"Upload processing failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _read_file(self, file_path: str, file_type: str) -> pd.DataFrame:
        """Read uploaded file based on type."""
        if file_type == "csv":
            return pd.read_csv(file_path)
        elif file_type in ["xlsx", "xls"]:
            return pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    def _validate_columns(self, df: pd.DataFrame) -> None:
        """Validate required columns in the uploaded file."""
        required_columns = [
            'trip_id',
            'departure_location_name',
            'departure_lat',
            'departure_lng',
            'arrival_location_name',
            'arrival_lat',
            'arrival_lng',
            'departure_datetime',
            'arrival_datetime_planned',
            'cargo_category',
            'cargo_weight_kg'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
    
    async def _process_trip_row(
        self,
        session: Session,
        company_id: uuid.UUID,
        row: pd.Series
    ) -> Dict[str, Any]:
        """Process a single trip row."""
        # Get company
        company = session.get(Company, company_id)
        if not company:
            raise ValueError(f"Company {company_id} not found")
        
        # Parse datetime fields
        departure_time = pd.to_datetime(row['departure_datetime'])
        arrival_time = pd.to_datetime(row['arrival_datetime_planned'])
        
        # Extract trip date
        trip_date = departure_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get route from Valhalla
        route_data = await self.valhalla.get_route(
            start_lat=row['departure_lat'],
            start_lng=row['departure_lng'],
            end_lat=row['arrival_lat'],
            end_lng=row['arrival_lng'],
            departure_time=departure_time
        )
        
        # Get return route to depot (if depot coordinates available)
        return_route_data = None
        if company.depot_lat and company.depot_lng:
            return_route_data = await self.valhalla.get_route(
                start_lat=row['arrival_lat'],
                start_lng=row['arrival_lng'],
                end_lat=company.depot_lat,
                end_lng=company.depot_lng
            )
        
        required_vehicle_category = self._parse_required_vehicle_category(
            row.get('required_vehicle_category')
        )
        if required_vehicle_category is None:
            required_vehicle_category = self._infer_required_vehicle_category_from_cargo(
                str(row['cargo_category'])
            )
        
        # Create trip
        trip_data = {
            'departure_point': row['departure_location_name'],
            'departure_lat': float(row['departure_lat']),
            'departure_lng': float(row['departure_lng']),
            'arrival_point': row['arrival_location_name'],
            'arrival_lat': float(row['arrival_lat']),
            'arrival_lng': float(row['arrival_lng']),
            'departure_datetime': departure_time,
            'arrival_datetime_planned': arrival_time,
            'cargo_category': row['cargo_category'],
            'material_type': row.get('material_type', 'solide'),
            'cargo_weight_kg': float(row['cargo_weight_kg']),
            'trip_date': trip_date,
            'uploaded_at': datetime.utcnow(),
            'route_polyline': route_data.get('polyline'),
            'route_distance_km': route_data.get('distance_km'),
            'route_duration_min': route_data.get('duration_min'),
            'route_calculated': True,
            'required_vehicle_category': required_vehicle_category,
            'vehicle_id': None,
            'company_id': company_id
        }
        
        # Add optional fields if present
        optional_fields = [
            'loading_window_start', 'loading_window_end',
            'delivery_window_start', 'delivery_window_end',
            'hazardous_material', 'temperature_requirement_celsius',
            'trip_priority', 'driver_name', 'notes'
        ]
        
        for field in optional_fields:
            if field in row and pd.notna(row[field]):
                if field in ['loading_window_start', 'loading_window_end',
                           'delivery_window_start', 'delivery_window_end']:
                    trip_data[field] = pd.to_datetime(row[field])
                else:
                    trip_data[field] = row[field]
        
        # Add return route data
        if return_route_data:
            trip_data.update({
                'return_route_polyline': return_route_data.get('polyline'),
                'return_distance_km': return_route_data.get('distance_km'),
                'return_duration_min': return_route_data.get('duration_min')
            })
        
        # Create trip in database
        trip = Trip(**trip_data)
        session.add(trip)
        session.commit()
        session.refresh(trip)
        
        # Check if we should create map markers
        await self._create_map_markers_if_needed(
            session=session,
            company_id=company_id,
            row=row,
            trip=trip
        )
        
        return {
            'trip_id': str(trip.id),
            'reference': row['trip_id'],
            'distance_km': route_data.get('distance_km'),
            'duration_min': route_data.get('duration_min'),
            'departure': row['departure_location_name'],
            'arrival': row['arrival_location_name'],
            'departure_time': departure_time.isoformat(),
            'estimated_arrival': (
                departure_time + timedelta(minutes=route_data.get('duration_min', 60))
            ).isoformat()
        }
    
    async def _find_compatible_vehicle(
        self,
        session: Session,
        company_id: uuid.UUID,
        row: pd.Series,
        departure_time: datetime
    ) -> uuid.UUID:
        """Find compatible vehicle for the trip."""
        # Get vehicle category based on cargo category
        vehicle_category = self._map_cargo_to_vehicle_category(row['cargo_category'])
        
        # Check for required vehicle category in row
        required_category = row.get('required_vehicle_category', vehicle_category)
        
        # Find available vehicles
        stmt = select(Vehicle).where(
            Vehicle.company_id == company_id,
            Vehicle.is_active == True,
            Vehicle.status == "disponible",
            Vehicle.category == required_category
        )
        
        vehicles = session.exec(stmt).all()
        
        if not vehicles:
            # If no exact match, try broader category
            stmt = select(Vehicle).where(
                Vehicle.company_id == company_id,
                Vehicle.is_active == True,
                Vehicle.status == "disponible"
            )
            vehicles = session.exec(stmt).all()
        
        if not vehicles:
            raise ValueError("No available vehicles found for this trip")
        
        # Select the first available vehicle
        # In production, you might want more sophisticated selection logic
        return vehicles[0].id

    def _parse_required_vehicle_category(self, raw: Any):
        """Parse VehicleCategory from either enum value (e.g. 'ag1_camion_frigorifique') or code (e.g. 'AG1')."""
        if raw is None:
            return None
        value = str(raw).strip()
        if not value:
            return None

        # Import locally to avoid import cycles at module import time
        from app.models.company_models import VehicleCategory

        try:
            return VehicleCategory(value)
        except Exception:
            pass
        try:
            return VehicleCategory[value]
        except Exception:
            return None

    def _infer_required_vehicle_category_from_cargo(self, cargo_category: str):
        """Infer VehicleCategory from cargo category when file doesn't provide it."""
        from app.models.company_models import VehicleCategory

        cargo_val = (cargo_category or "").lower()
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

        # Fallback
        return VehicleCategory.AG1
    
    def _map_cargo_to_vehicle_category(self, cargo_category: str) -> str:
        """Map cargo category to vehicle category."""
        # Simplified mapping - expand based on your requirements
        mapping = {
            "A01": "AG1",  # produits_frais -> camion_frigorifique
            "A02": "AG2",  # produits_surgeles -> camion_refrigere
            "B01": "BT1",  # materiaux_vrac -> camion_benne
            "B02": "BT4",  # materiaux_solides -> camion_plateau_ridelles
            "I01": "IN2",  # produits_finis -> fourgon_ferme
            "C01": "CH2",  # chimiques_liquides -> camion_citerne_chimique
        }
        
        return mapping.get(cargo_category, "AG1")  # Default to refrigerated truck
    
    async def _create_map_markers_if_needed(
        self,
        session: Session,
        company_id: uuid.UUID,
        row: pd.Series,
        trip: Trip
    ):
        """Create map markers for departure and arrival locations if they don't exist."""
        # Check for departure marker
        dep_stmt = select(MapMarker).where(
            MapMarker.company_id == company_id,
            MapMarker.lat == trip.departure_lat,
            MapMarker.lng == trip.departure_lng
        )
        dep_marker = session.exec(dep_stmt).first()
        
        if not dep_marker and trip.departure_lat and trip.departure_lng:
            dep_marker = MapMarker(
                company_id=company_id,
                name=trip.departure_point,
                lat=trip.departure_lat,
                lng=trip.departure_lng,
                marker_type="depot" if "depot" in trip.departure_point.lower() else "location",
                address=None
            )
            session.add(dep_marker)
        
        # Check for arrival marker
        arr_stmt = select(MapMarker).where(
            MapMarker.company_id == company_id,
            MapMarker.lat == trip.arrival_lat,
            MapMarker.lng == trip.arrival_lng
        )
        arr_marker = session.exec(arr_stmt).first()
        
        if not arr_marker and trip.arrival_lat and trip.arrival_lng:
            arr_marker = MapMarker(
                company_id=company_id,
                name=trip.arrival_point,
                lat=trip.arrival_lat,
                lng=trip.arrival_lng,
                marker_type="warehouse" if "warehouse" in trip.arrival_point.lower() else "location",
                address=None
            )
            session.add(arr_marker)
        
        if dep_marker or arr_marker:
            session.commit()
    
    async def _generate_ttr_matrix(self, trips: List[Dict]) -> Dict[Tuple[int, int], Dict]:
        """Generate Trip-to-Trip travel time matrix."""
        if len(trips) < 2:
            return {}
        
        # Prepare trip data for TTR calculation
        trip_data = []
        for trip in trips:
            trip_data.append({
                'departure_lat': trip.get('departure_lat'),
                'departure_lng': trip.get('departure_lng'),
                'arrival_lat': trip.get('arrival_lat'),
                'arrival_lng': trip.get('arrival_lng'),
                'route_duration_min': trip.get('duration_min', 60),
                'arrival_datetime_planned': trip.get('estimated_arrival'),
                'departure_datetime': trip.get('departure_time'),
                'service_time_min': 30  # Default service time
            })
        
        # Calculate TTR matrix using Valhalla
        ttr_result = await self.valhalla.calculate_trip_to_trip_matrix(trip_data)
        
        return ttr_result.get('matrix', {})
    
    async def validate_trip_file(
        self,
        file_path: str,
        file_type: str = "csv"
    ) -> Dict[str, Any]:
        """
        Validate trip file without saving to database.
        Returns validation results and preview.
        """
        try:
            df = self._read_file(file_path, file_type)
            
            # Basic validation
            validation_errors = []
            preview_data = []
            
            # Check required columns
            required_columns = [
                'trip_id',
                'departure_location_name',
                'departure_lat',
                'departure_lng',
                'arrival_location_name',
                'arrival_lat',
                'arrival_lng',
                'departure_datetime',
                'arrival_datetime_planned',
                'cargo_category',
                'cargo_weight_kg'
            ]
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                validation_errors.append(f"Missing columns: {missing_columns}")
            
            # Check data types and sample values
            for idx, row in df.head(5).iterrows():  # First 5 rows as preview
                preview_row = {}
                for col in df.columns:
                    preview_row[col] = str(row[col]) if pd.notna(row[col]) else None
                preview_data.append(preview_row)
            
            # Check for datetime parsing
            try:
                df['departure_datetime'] = pd.to_datetime(df['departure_datetime'])
                df['arrival_datetime_planned'] = pd.to_datetime(df['arrival_datetime_planned'])
            except Exception as e:
                validation_errors.append(f"Date parsing error: {str(e)}")
            
            # Check coordinate ranges
            lat_cols = [c for c in df.columns if 'lat' in c.lower()]
            lng_cols = [c for c in df.columns if 'lng' in c.lower()]
            
            for col in lat_cols:
                if col in df.columns:
                    invalid_lat = df[(df[col] < -90) | (df[col] > 90)]
                    if not invalid_lat.empty:
                        validation_errors.append(f"Invalid latitude values in {col}")
            
            for col in lng_cols:
                if col in df.columns:
                    invalid_lng = df[(df[col] < -180) | (df[col] > 180)]
                    if not invalid_lng.empty:
                        validation_errors.append(f"Invalid longitude values in {col}")
            
            return {
                'valid': len(validation_errors) == 0,
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': list(df.columns),
                'preview': preview_data,
                'errors': validation_errors,
                'warnings': []  # Add warnings here if needed
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }