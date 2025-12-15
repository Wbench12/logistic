import httpx
from typing import Dict, List, Tuple, Optional, Any
import polyline as pl
from datetime import datetime, timedelta
import asyncio
import math

class ValhallaService:
    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_route(
        self,
        start_lat: float,
        start_lng: float,
        end_lat: float,
        end_lng: float,
        costing: str = "truck",
        departure_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get route from Valhalla with detailed information."""
        try:
            # Convert datetime to ISO format for Valhalla
            date_time_str = None
            if departure_time:
                date_time_str = departure_time.isoformat()
            
            request_body = {
                "locations": [
                    {"lat": start_lat, "lon": start_lng},
                    {"lat": end_lat, "lon": end_lng}
                ],
                "costing": costing,
                "directions_options": {"units": "kilometers"},
                "date_time": {
                    "type": departure_time and "departure" or "current",
                    "value": date_time_str
                } if departure_time else None
            }
            
            response = await self.client.post(
                f"{self.base_url}/route",
                json=request_body
            )
            
            if response.status_code == 200:
                data = response.json()
                leg = data["trip"]["legs"][0]
                
                return {
                    "distance_km": leg["summary"]["length"] / 1000,  # Convert to km
                    "duration_min": leg["summary"]["time"] / 60,     # Convert to minutes
                    "polyline": data["trip"]["legs"][0]["shape"],
                    "maneuvers": leg["maneuvers"],
                    "success": True
                }
            else:
                # Fallback to haversine if Valhalla fails
                return await self._get_fallback_route(start_lat, start_lng, end_lat, end_lng)
                
        except Exception as e:
            # Fallback to haversine calculation if Valhalla fails
            return await self._get_fallback_route(start_lat, start_lng, end_lat, end_lng)
    
    async def _get_fallback_route(
        self,
        start_lat: float,
        start_lng: float,
        end_lat: float,
        end_lng: float
    ) -> Dict[str, Any]:
        """Fallback route calculation using haversine distance."""
        distance = self._haversine_distance(
            start_lat, start_lng, end_lat, end_lng
        )
        
        # Create a simple polyline for the fallback
        encoded_polyline = pl.encode([(start_lat, start_lng), (end_lat, end_lng)])
        
        return {
            "distance_km": distance,
            "duration_min": distance / 40 * 60,  # Assume 40 km/h average for trucks
            "polyline": encoded_polyline,
            "maneuvers": [],
            "success": False,
            "fallback": True
        }
    
    async def get_matrix(
        self,
        locations: List[Tuple[float, float]],
        costing: str = "truck"
    ) -> Dict[str, Any]:
        """Get time and distance matrix for multiple locations."""
        try:
            request_body = {
                "sources": [{"lat": lat, "lon": lng} for lat, lng in locations],
                "targets": [{"lat": lat, "lon": lng} for lat, lng in locations],
                "costing": costing,
                "matrix_locations": len(locations)
            }
            
            response = await self.client.post(
                f"{self.base_url}/sources_to_targets",
                json=request_body
            )
            
            if response.status_code == 200:
                data = response.json()

                raw = data.get("sources_to_targets")
                durations: List[List[float]] = []
                distances: List[List[float]] = []

                if isinstance(raw, list) and raw and isinstance(raw[0], list):
                    # Valhalla commonly returns a matrix of objects: {time, distance, ...}
                    first_cell = raw[0][0] if raw[0] else None
                    if isinstance(first_cell, dict):
                        durations = [[float((cell or {}).get("time", 0.0)) for cell in row] for row in raw]
                        # Valhalla returns distance in kilometers; normalize to meters for consistency
                        distances = [[float((cell or {}).get("distance", 0.0)) * 1000.0 for cell in row] for row in raw]
                    else:
                        # Some deployments may return numeric seconds directly
                        durations = [[float(cell or 0.0) for cell in row] for row in raw]

                raw_distances = data.get("distances")
                if not distances and isinstance(raw_distances, list) and raw_distances and isinstance(raw_distances[0], list):
                    distances = [[float(cell or 0.0) for cell in row] for row in raw_distances]

                if not durations:
                    return await self._get_fallback_matrix(locations)

                return {
                    "durations": durations,  # seconds
                    "distances": distances,  # meters (best-effort)
                    "success": True
                }
            else:
                return await self._get_fallback_matrix(locations)
                
        except Exception as e:
            return await self._get_fallback_matrix(locations)
    
    async def _get_fallback_matrix(self, locations: List[Tuple[float, float]]) -> Dict[str, Any]:
        """Fallback matrix calculation using haversine distance."""
        n = len(locations)
        durations = [[0.0] * n for _ in range(n)]
        distances = [[0.0] * n for _ in range(n)]
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    dist = self._haversine_distance(
                        locations[i][0], locations[i][1],
                        locations[j][0], locations[j][1]
                    )
                    distances[i][j] = dist * 1000  # Convert to meters
                    durations[i][j] = (dist / 40) * 3600  # seconds at 40 km/h
        
        return {
            "durations": durations,
            "distances": distances,
            "success": False,
            "fallback": True
        }
    
    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """Calculate haversine distance between two points in km."""
        R = 6371  # Earth's radius in km
        
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def decode_polyline(self, encoded_polyline: str) -> List[Tuple[float, float]]:
        """Decode a polyline string into latitude/longitude coordinates."""
        try:
            return pl.decode(encoded_polyline)
        except:
            return []
    
    def encode_polyline(self, coordinates: List[Tuple[float, float]]) -> str:
        """Encode latitude/longitude coordinates into a polyline string."""
        return pl.encode(coordinates)
    
    async def calculate_trip_to_trip_matrix(
        self,
        trips: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate Trip-to-Trip travel time matrix for optimization.
        
        Args:
            trips: List of trips with departure and arrival coordinates
        """
        # Extract all unique locations
        locations = []
        location_to_trip_map = {}  # Map location index to trip index
        
        for i, trip in enumerate(trips):
            # Add departure location
            dep_key = (trip['departure_lat'], trip['departure_lng'])
            if dep_key not in location_to_trip_map:
                location_to_trip_map[dep_key] = {'type': 'departure', 'trip_index': i}
                locations.append(dep_key)
            
            # Add arrival location
            arr_key = (trip['arrival_lat'], trip['arrival_lng'])
            if arr_key not in location_to_trip_map:
                location_to_trip_map[arr_key] = {'type': 'arrival', 'trip_index': i}
                locations.append(arr_key)
        
        # Get matrix from Valhalla
        matrix_result = await self.get_matrix(locations)
        
        # Create TTR matrix
        ttr_matrix = {}
        
        for i, trip_i in enumerate(trips):
            for j, trip_j in enumerate(trips):
                if i != j:
                    # Find arrival location of trip_i
                    arr_key_i = (trip_i['arrival_lat'], trip_i['arrival_lng'])
                    arr_idx_i = locations.index(arr_key_i)
                    
                    # Find departure location of trip_j
                    dep_key_j = (trip_j['departure_lat'], trip_j['departure_lng'])
                    dep_idx_j = locations.index(dep_key_j)
                    
                    # Get travel time and distance
                    travel_time_min = matrix_result['durations'][arr_idx_i][dep_idx_j] / 60
                    travel_distance_km = matrix_result['distances'][arr_idx_i][dep_idx_j] / 1000
                    
                    ttr_matrix[(i, j)] = {
                        'travel_time_min': travel_time_min,
                        'travel_distance_km': travel_distance_km,
                        'feasible': self._check_ttr_feasibility(trip_i, trip_j, travel_time_min)
                    }
        
        return {
            'matrix': ttr_matrix,
            'locations': locations,
            'success': matrix_result.get('success', False),
            'fallback': matrix_result.get('fallback', False)
        }
    
    def _check_ttr_feasibility(
        self,
        trip_i: Dict[str, Any],
        trip_j: Dict[str, Any],
        travel_time_min: float
    ) -> bool:
        """Check if trip sequencing is feasible based on time windows."""
        # Calculate earliest finish time of trip_i
        trip_i_duration = trip_i.get('route_duration_min', 60)
        trip_i_service = trip_i.get('service_time_min', 30)
        
        # Get time windows
        trip_i_end = trip_i.get('arrival_datetime_planned')
        trip_j_start = trip_j.get('departure_datetime')
        
        if not trip_i_end or not trip_j_start:
            # If no specific times, assume feasible
            return True
        
        # Convert to datetime if strings
        if isinstance(trip_i_end, str):
            trip_i_end = datetime.fromisoformat(trip_i_end)
        if isinstance(trip_j_start, str):
            trip_j_start = datetime.fromisoformat(trip_j_start)
        
        # Calculate earliest possible start at trip_j
        earliest_arrival_at_j = trip_i_end + timedelta(minutes=travel_time_min)
        
        # Check if we can start trip_j on time
        return earliest_arrival_at_j <= trip_j_start
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()