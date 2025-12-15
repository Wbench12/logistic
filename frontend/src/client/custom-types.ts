// Specific types based on your API description

export interface Trip {
  id: string
  departure_point: string
  departure_lat: number
  departure_lng: number
  arrival_point: string
  arrival_lat: number
  arrival_lng: number
  departure_datetime: string
  arrival_datetime_planned: string
  cargo_category: string
  cargo_weight_kg: number
  status: "planifie" | "en_cours" | "termine" | "annule"
  route_polyline?: string // Encoded string
  assigned_vehicle_id?: string
  estimated_arrival?: string
  sequence_order?: number
}

export interface MapData {
  trips: Array<Trip & { optimized: boolean; departure: { name: string }; arrival: { name: string } }>
  markers: Array<{
    id: string
    name: string
    lat: number
    lng: number
    type: "depot" | "warehouse" | "customer"
  }>
  bounds: { north: number; south: number; east: number; west: number }
}

export interface OptimizationResult {
  message: string
  details: {
    trips_optimized: number
    km_saved: number
  }
}

export interface KPIData {
  date: string
  optimized: boolean
  savings: {
    km_saved: number
    fuel_saved_liters: number
    co2_saved_kg: number
    cost_saved_usd: number
  }
  summary: {
    trips_contributed: number
    vehicles_used: number
  }
}