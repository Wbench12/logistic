import { Box } from "@chakra-ui/react" // Removed useColorModeValue from here
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from "react-leaflet"
import polyline from "@mapbox/polyline"
import "leaflet/dist/leaflet.css"
import L from "leaflet"
import { useEffect } from "react"
// Import from your local UI helper
import { useColorModeValue } from "@/components/ui/color-mode"

// Fix Leaflet default icon issue
import icon from "leaflet/dist/images/marker-icon.png"
import iconShadow from "leaflet/dist/images/marker-shadow.png"

const DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
})
L.Marker.prototype.options.icon = DefaultIcon

// Define types locally since we aren't using the custom-types file yet
interface MapData {
  trips: any[]
  markers: any[]
  bounds: { north: number; south: number; east: number; west: number }
}

interface TripMapProps {
  data: MapData | undefined
  onMapClick?: (lat: number, lng: number) => void
}

const MapUpdater = ({ bounds }: { bounds: MapData["bounds"] }) => {
  const map = useMap()
  useEffect(() => {
    if (bounds) {
      map.fitBounds([
        [bounds.south, bounds.west],
        [bounds.north, bounds.east],
      ])
    }
  }, [bounds, map])
  return null
}

const TripMap = ({ data, onMapClick }: TripMapProps) => {
  const isDark = useColorModeValue(false, true)

  if (!data) return <Box h="500px" bg="bg.subtle" borderRadius="xl" />

  return (
    <Box
      h="600px"
      w="full"
      borderRadius="xl"
      overflow="hidden"
      boxShadow="md"
      borderWidth="1px"
      borderColor="border.subtle"
      zIndex={0}
    >
      <MapContainer
        center={[36.753, 3.058]}
        zoom={6}
        style={{ height: "100%", width: "100%" }}
        // @ts-ignore
        whenReady={(map) => {
            if(onMapClick) {
                map.target.on("click", (e: any) => {
                    onMapClick(e.latlng.lat, e.latlng.lng)
                })
            }
        }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url={isDark 
            ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            : "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          }
        />

        {data.bounds && <MapUpdater bounds={data.bounds} />}

        {data.trips.map((trip) => {
          if (!trip.route_polyline) return null
          const positions = polyline.decode(trip.route_polyline)
          
          return (
            <Polyline
              key={trip.id}
              positions={positions}
              pathOptions={{
                color: trip.optimized ? "#009688" : "#2196f3",
                weight: 4,
                opacity: 0.8,
              }}
            >
              <Popup>
                <strong>{trip.departure.name} ➔ {trip.arrival.name}</strong><br />
                Statut: {trip.status}<br />
                Arrivée estimée: {new Date(trip.estimated_arrival || "").toLocaleTimeString()}
              </Popup>
            </Polyline>
          )
        })}

        {data.markers.map((marker) => (
          <Marker key={marker.id} position={[marker.lat, marker.lng]}>
            <Popup>
              <strong>{marker.name}</strong><br />
              Type: {marker.type}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </Box>
  )
}

export default TripMap