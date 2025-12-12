import {
  Badge,
  Box,
  CardBody,
  CardRoot,
  Container,
  chakra,
  Flex,
  Heading,
  Icon,
  SimpleGrid,
  Text,
} from "@chakra-ui/react"
import { type ReactNode, useEffect, useState } from "react"
import type { IconType } from "react-icons"
import {
  FiActivity,
  FiClock,
  FiDroplet,
  FiFeather,
  FiTruck,
} from "react-icons/fi"

type TripStatus = "in_progress" | "planned" | "completed"

interface DailyTrip {
  id: string
  departure_point: string
  arrival_point: string
  status: TripStatus
  vehicle_id: string
  departure_datetime: string
}

interface EsgContribution {
  co2_saved_kg: number
  trees_equivalent: number
  fuel_saved_liters: number
}

interface DashboardMetrics {
  trips_in_progress: number
  vehicles_distributed: number
  km_reduced_today: number
  fuel_saved_today: number
  daily_trips: DailyTrip[]
  esg_contribution: EsgContribution
}

interface StatCardProps {
  icon: IconType
  label: string
  value: ReactNode
  helpText: string
  color: string
  trend?: string
}

const DashboardPage = () => {
  const [metrics, setMetrics] = useState<DashboardMetrics>({
    trips_in_progress: 8,
    vehicles_distributed: 15,
    km_reduced_today: 450.5,
    fuel_saved_today: 135.15,
    daily_trips: [],
    esg_contribution: {
      co2_saved_kg: 311.85,
      trees_equivalent: 14,
      fuel_saved_liters: 135.15,
    },
  })

  useEffect(() => {
    const mockTrips: DailyTrip[] = [
      {
        id: "1",
        departure_point: "Oran",
        arrival_point: "Alger",
        status: "in_progress",
        vehicle_id: "V-001",
        departure_datetime: "2025-01-10T08:00:00",
      },
      {
        id: "2",
        departure_point: "Constantine",
        arrival_point: "Annaba",
        status: "planned",
        vehicle_id: "V-002",
        departure_datetime: "2025-01-10T09:30:00",
      },
      {
        id: "3",
        departure_point: "Alger",
        arrival_point: "Oran",
        status: "in_progress",
        vehicle_id: "V-003",
        departure_datetime: "2025-01-10T07:15:00",
      },
    ]

    setMetrics((prev) => ({ ...prev, daily_trips: mockTrips }))
  }, [])

  return (
    <Container maxW="full" py={8} px={6}>
      <Box mb={8}>
        <Flex justifyContent="space-between" alignItems="center" mb={2}>
          <Heading
            size="xl"
            bgGradient="linear(to-r, teal.400, blue.500)"
            bgClip="text"
          >
            Tableau de Bord
          </Heading>
          <Badge
            colorScheme="teal"
            fontSize="md"
            px={3}
            py={1}
            borderRadius="full"
          >
            Aujourd'hui: {new Date().toLocaleDateString("fr-FR")}
          </Badge>
        </Flex>
        <Text color="gray.600" fontSize="lg">
          Vue d'ensemble de votre activité logistique
        </Text>
      </Box>

      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} gap={6} mb={8}>
        <StatCard
          icon={FiActivity}
          label="Trajets en Cours"
          value={metrics.trips_in_progress}
          helpText="Véhicules actifs"
          color="blue.500"
          trend="+2 depuis hier"
        />
        <StatCard
          icon={FiTruck}
          label="Véhicules Distribués"
          value={metrics.vehicles_distributed}
          helpText="Flotte active"
          color="purple.500"
          trend="+5 ce mois"
        />
        <StatCard
          icon={FiActivity}
          label="KM Réduits"
          value={`${metrics.km_reduced_today.toFixed(1)} km`}
          helpText="Économie trajet"
          color="teal.500"
          trend="10% amélioration"
        />
        <StatCard
          icon={FiDroplet}
          label="Carburant Économisé"
          value={`${metrics.fuel_saved_today.toFixed(1)} L`}
          helpText="Économie carburant"
          color="orange.500"
          trend="-15% consommation"
        />
      </SimpleGrid>

      <CardRoot
        variant="elevated"
        borderRadius="xl"
        mb={8}
        bg="green.50"
        borderWidth={2}
        borderColor="green.200"
      >
        <CardBody p={6}>
          <Flex alignItems="center" mb={4}>
            <Icon as={FiFeather} boxSize={6} color="green.600" mr={3} />
            <Heading size="md" color="green.800">
              Contribution ESG
            </Heading>
          </Flex>

          <SimpleGrid columns={{ base: 1, md: 3 }} gap={6}>
            <Box>
              <Text fontSize="sm" color="gray.600" mb={1}>
                CO₂ Évité
              </Text>
              <Text fontSize="2xl" fontWeight="bold" color="green.700">
                {metrics.esg_contribution.co2_saved_kg.toFixed(1)} kg
              </Text>
            </Box>
            <Box>
              <Text fontSize="sm" color="gray.600" mb={1}>
                Équivalent Arbres
              </Text>
              <Text fontSize="2xl" fontWeight="bold" color="green.700">
                🌳 {metrics.esg_contribution.trees_equivalent}
              </Text>
            </Box>
            <Box>
              <Text fontSize="sm" color="gray.600" mb={1}>
                Carburant Économisé
              </Text>
              <Text fontSize="2xl" fontWeight="bold" color="green.700">
                {metrics.esg_contribution.fuel_saved_liters.toFixed(1)} L
              </Text>
            </Box>
          </SimpleGrid>

          <Box mt={4}>
            <Flex justifyContent="space-between" mb={2}>
              <Text fontSize="xs" color="gray.600">
                Objectif mensuel
              </Text>
              <Text fontSize="xs" color="gray.600">
                65% atteint
              </Text>
            </Flex>
            <Box
              height="8px"
              bg="green.100"
              borderRadius="full"
              overflow="hidden"
            >
              <Box
                height="100%"
                bg="green.500"
                width="65%"
                transition="width 0.2s ease"
              />
            </Box>
          </Box>
        </CardBody>
      </CardRoot>

      <CardRoot variant="elevated" borderRadius="xl">
        <CardBody p={6}>
          <Flex justifyContent="space-between" alignItems="center" mb={6}>
            <Heading size="md">Trajets du Jour</Heading>
            <Badge colorScheme="blue" fontSize="sm" px={3} py={1}>
              {metrics.daily_trips.length} trajets
            </Badge>
          </Flex>

          <Box overflowX="auto">
            <ChakraTable
              width="100%"
              borderCollapse="separate"
              borderSpacing="0 12px"
            >
              <ChakraThead>
                <ChakraTr>
                  {[
                    "ID",
                    "Départ",
                    "Arrivée",
                    "Heure",
                    "Véhicule",
                    "Statut",
                  ].map((heading) => (
                    <ChakraTh
                      key={heading}
                      textAlign="left"
                      fontSize="sm"
                      color="gray.500"
                      px={3}
                    >
                      {heading}
                    </ChakraTh>
                  ))}
                </ChakraTr>
              </ChakraThead>
              <ChakraTbody>
                {metrics.daily_trips.length > 0 ? (
                  metrics.daily_trips.map((trip) => (
                    <ChakraTr
                      key={trip.id}
                      bg="white"
                      borderRadius="xl"
                      boxShadow="sm"
                      _hover={{ bg: "gray.50" }}
                    >
                      <ChakraTd fontWeight="medium">{trip.id}</ChakraTd>
                      <ChakraTd>{trip.departure_point}</ChakraTd>
                      <ChakraTd>{trip.arrival_point}</ChakraTd>
                      <ChakraTd>
                        <Flex alignItems="center">
                          <Icon as={FiClock} mr={2} color="gray.500" />
                          {new Date(trip.departure_datetime).toLocaleTimeString(
                            "fr-FR",
                            {
                              hour: "2-digit",
                              minute: "2-digit",
                            },
                          )}
                        </Flex>
                      </ChakraTd>
                      <ChakraTd>
                        <Badge colorScheme="gray" variant="subtle">
                          {trip.vehicle_id}
                        </Badge>
                      </ChakraTd>
                      <ChakraTd>
                        <Badge colorScheme={getStatusColor(trip.status)}>
                          {getStatusLabel(trip.status)}
                        </Badge>
                      </ChakraTd>
                    </ChakraTr>
                  ))
                ) : (
                  <ChakraTr>
                    <ChakraTd colSpan={6} textAlign="center" py={8}>
                      <Text color="gray.500">Aucun trajet aujourd'hui</Text>
                    </ChakraTd>
                  </ChakraTr>
                )}
              </ChakraTbody>
            </ChakraTable>
          </Box>
        </CardBody>
      </CardRoot>
    </Container>
  )
}

const StatCard = ({
  icon,
  label,
  value,
  helpText,
  color,
  trend,
}: StatCardProps) => {
  const accentColor = color.includes(".") ? color.split(".")[0] : color

  return (
    <CardRoot variant="elevated" borderRadius="xl" overflow="hidden">
      <CardBody p={6}>
        <Flex justifyContent="space-between" alignItems="flex-start">
          <Box>
            <Text fontSize="sm" color="gray.600" mb={2}>
              {label}
            </Text>
            <Text fontSize="3xl" fontWeight="bold" color={color}>
              {value}
            </Text>
            <Text fontSize="xs" color="gray.500" mt={2}>
              {helpText}
            </Text>
          </Box>
          <Flex
            bg={`${accentColor}.50`}
            p={3}
            borderRadius="lg"
            alignItems="center"
            justifyContent="center"
          >
            <Icon as={icon} boxSize={6} color={color} />
          </Flex>
        </Flex>
        {trend && (
          <Badge colorScheme="green" mt={3} fontSize="xs">
            ↗ {trend}
          </Badge>
        )}
      </CardBody>
    </CardRoot>
  )
}

const ChakraTable = chakra("table")
const ChakraThead = chakra("thead")
const ChakraTbody = chakra("tbody")
const ChakraTr = chakra("tr")
const ChakraTh = chakra("th")
const ChakraTd = chakra("td")

const getStatusColor = (status: TripStatus) => {
  switch (status) {
    case "in_progress":
      return "blue"
    case "planned":
      return "purple"
    case "completed":
      return "green"
    default:
      return "gray"
  }
}

const getStatusLabel = (status: TripStatus) => {
  switch (status) {
    case "in_progress":
      return "En cours"
    case "planned":
      return "Planifié"
    case "completed":
      return "Terminé"
    default:
      return status
  }
}

export default DashboardPage
