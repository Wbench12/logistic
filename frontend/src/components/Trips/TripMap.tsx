import { Box, Badge, Text, VStack } from "@chakra-ui/react"
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap, useMapEvents } from "react-leaflet"
import polyline from "@mapbox/polyline"
import "leaflet/dist/leaflet.css"
import L from "leaflet"
import { useEffect } from "react"
import { useColorModeValue } from "@/components/ui/color-mode"

// --- Fix Leaflet Default Icons in React ---
import icon from "leaflet/dist/images/marker-icon.png"
import iconShadow from "leaflet/dist/images/marker-shadow.png"

const DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
})
L.Marker.prototype.options.icon = DefaultIcon

// --- Types ---
export interface DraftPoint {
  lat: number;
  lng: number;
  name?: string;
}

interface TripMapProps {
  // Data from Backend GET /api/v1/trips/map/{date}
  data: {
    trips: any[];
    markers: any[];
    bounds: { north: number; south: number; east: number; west: number };
  } | undefined;
  
  // Draft State (from TripManagement)
  draftDeparture?: DraftPoint | null;
  draftArrival?: DraftPoint | null;
  
  // Event Handlers
  onMapClick?: (lat: number, lng: number) => void;
}

// --- Helper Components ---

// Captures clicks on the map to trigger geocoding in parent
const MapClickHandler = ({ onClick }: { onClick: (lat: number, lng: number) => void }) => {
  useMapEvents({
    click(e) {
      onClick(e.latlng.lat, e.latlng.lng)
    },
  })
  return null
}

// Updates map view/zoom when data changes
const MapUpdater = ({ bounds, draftDeparture, draftArrival }: { bounds: any, draftDeparture?: DraftPoint | null, draftArrival?: DraftPoint | null }) => {
  const map = useMap()
  
  useEffect(() => {
    // Priority 1: If drafting, fit to show start and end points
    if (draftDeparture && draftArrival) {
        const group = new L.FeatureGroup([
            L.marker([draftDeparture.lat, draftDeparture.lng]),
            L.marker([draftArrival.lat, draftArrival.lng])
        ]);
        map.fitBounds(group.getBounds().pad(0.2));
    }
    // Priority 2: Fit to backend provided bounds (All trips of the day)
    else if (bounds) {
      map.fitBounds([
        [bounds.south, bounds.west],
        [bounds.north, bounds.east],
      ], { padding: [50, 50] })
    }
  }, [bounds, map, draftDeparture, draftArrival])
  
  return null
}

// --- Main Component ---

const TripMap = ({ data, draftDeparture, draftArrival, onMapClick }: TripMapProps) => {
  const isDark = useColorModeValue(false, true)

  return (
    <Box
      h="600px"
      w="full"
      borderRadius="xl"
      overflow="hidden"
      boxShadow="md"
      borderWidth="1px"
      borderColor="border.subtle"
      zIndex={0} // Keep z-index low so modals appear on top
    >
      <MapContainer
        center={[36.753, 3.058]} // Default Center (Algiers)
        zoom={6}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url={isDark 
            ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            : "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          }
        />

        {/* View Controller */}
        <MapUpdater bounds={data?.bounds} draftDeparture={draftDeparture} draftArrival={draftArrival} />
        
        {/* Click Listener */}
        {onMapClick && <MapClickHandler onClick={onMapClick} />}

        {/* --- 1. RENDER SAVED TRIPS (From Backend) --- */}
        {data?.trips?.map((trip: any) => {
          let positions: any = null
          let isApproximate = false

          // Case A: Valhalla Polyline exists (Precision 6)
          if (trip.route_polyline) {
             try {
                positions = polyline.decode(trip.route_polyline, 6)
             } catch (e) {
                console.warn("Polyline decode error for trip", trip.id, e)
             }
          }

          // Case B: Fallback (Straight Line) if polyline is missing/invalid
          // This ensures the trip is visible even if the backend hasn't calculated the route yet
          if (!positions && trip.departure && trip.arrival) {
             positions = [
                [trip.departure.lat, trip.departure.lng],
                [trip.arrival.lat, trip.arrival.lng]
             ]
             isApproximate = true
          }

          // If we still have no coordinates, skip rendering
          if (!positions) return null

          // Style based on status
          const color = trip.status === 'en_cours' ? '#ed8936' // Orange
                      : trip.optimized ? '#38a169' // Green
                      : '#3182ce'; // Blue

          return (
            <Polyline
              key={trip.id}
              positions={positions}
              pathOptions={{ 
                color: color,
                weight: isApproximate ? 3 : 5, 
                opacity: 0.8,
                dashArray: isApproximate ? "10, 10" : undefined // Dashed if approximate
              }}
            >
              <Popup>
                <VStack align="start" gap={1} minW="200px">
                  <Text fontWeight="bold" fontSize="sm">
                    {trip.departure.name} ➔ {trip.arrival.name}
                  </Text>
                  <Badge colorPalette={trip.optimized ? "green" : "blue"} variant="solid">
                    {trip.status}
                  </Badge>
                  
                  {isApproximate && (
                    <Text fontSize="xs" color="red.500" fontStyle="italic">
                      Tracé approximatif (calcul en cours)
                    </Text>
                  )}

                  <Box fontSize="xs" color="gray.500">
                    <Text>Poids: {trip.cargo_weight_kg} kg</Text>
                    {trip.route_distance_km && (
                        <Text>Distance: {trip.route_distance_km.toFixed(1)} km</Text>
                    )}
                    {trip.estimated_arrival && (
                        <Text>ETA: {new Date(trip.estimated_arrival).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</Text>
                    )}
                  </Box>
                </VStack>
              </Popup>
            </Polyline>
          )
        })}

        {/* --- 2. RENDER DRAFT MARKERS (Creating New Trip) --- */}
        {draftDeparture && (
          <Marker position={[draftDeparture.lat, draftDeparture.lng]}>
            <Popup>🚩 Départ: {draftDeparture.name}</Popup>
          </Marker>
        )}
        
        {draftArrival && (
          <Marker position={[draftArrival.lat, draftArrival.lng]}>
            <Popup>🏁 Arrivée: {draftArrival.name}</Popup>
          </Marker>
        )}

      </MapContainer>
    </Box>
  )
}

export default TripMap