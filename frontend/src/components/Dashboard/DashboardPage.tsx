import {
  Box,
  CardBody,
  CardRoot,
  Container,
  Flex,
  Heading,
  Icon,
  SimpleGrid,
  Text,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import {
  FiActivity,
  FiDollarSign,
  FiDroplet,
  FiFeather,
  FiTruck,
} from "react-icons/fi";

import { ExtendedTripsService } from "@/client/services/ExtendedTripsService";
import { SkeletonText } from "@/components/ui/skeleton";

const DashboardPage = () => {
  const today = new Date().toISOString().split("T")[0];

  const { data: kpiData, isLoading } = useQuery({
    queryKey: ["dashboardKPI", today],
    queryFn: () => ExtendedTripsService.getKPIs(today),
  });

  // Safe defaults if API returns null (e.g., no data for today yet)
  const savings = kpiData?.savings || {
    km_saved: 0,
    fuel_saved_liters: 0,
    co2_saved_kg: 0,
    cost_saved_usd: 0,
  };
  const summary = kpiData?.summary || {
    trips_contributed: 0,
    vehicles_used: 0,
  };

  if (isLoading) {
    return (
      <Container maxW="full" py={8} px={6}>
        <SkeletonText noOfLines={5} gap={6} />
      </Container>
    );
  }

  return (
    <Container maxW="full" py={8} px={{ base: 4, md: 8 }}>
      <Box mb={8}>
        <Heading size="2xl" letterSpacing="tight" mb={2}>
          Tableau de Bord
        </Heading>
        <Text color="fg.muted" fontSize="lg">
          Performance du {new Date().toLocaleDateString()}
        </Text>
      </Box>

      {/* KPI Cards */}
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} gap={6} mb={8}>
        <StatCard
          icon={FiTruck}
          label="Trajets Totaux"
          value={summary.trips_contributed}
          color="blue"
        />
        <StatCard
          icon={FiActivity}
          label="KM Économisés"
          value={savings.km_saved.toFixed(1)}
          unit="km"
          color="teal"
        />
        <StatCard
          icon={FiDollarSign}
          label="Économies (Est.)"
          value={savings.cost_saved_usd.toFixed(2)}
          unit="$"
          color="green"
        />
        <StatCard
          icon={FiDroplet}
          label="Carburant"
          value={savings.fuel_saved_liters.toFixed(1)}
          unit="L"
          color="orange"
        />
      </SimpleGrid>

      {/* ESG Contribution Card */}
      <CardRoot
        variant="elevated"
        borderRadius="2xl"
        mb={8}
        bgGradient="to-br"
        gradientFrom="brand.700"
        gradientTo="accent.500"
        color="white"
        boxShadow="lg"
        border="none"
      >
        <CardBody p={{ base: 6, md: 8 }}>
          <Flex
            alignItems="center"
            mb={8}
            borderBottomWidth="1px"
            borderColor="whiteAlpha.300"
            pb={4}
          >
            <Box p={2} bg="whiteAlpha.200" borderRadius="lg" mr={4}>
              <Icon as={FiFeather} boxSize={6} color="white" />
            </Box>
            <Box>
              <Heading size="lg" fontWeight="bold">
                Impact Écologique
              </Heading>
              <Text fontSize="sm" opacity={0.9}>
                Réductions grâce à l'optimisation
              </Text>
            </Box>
          </Flex>

          <SimpleGrid columns={{ base: 1, md: 2 }} gap={8}>
            <EsgMetric
              label="CO₂ Évité"
              value={savings.co2_saved_kg.toFixed(1)}
              unit="kg"
            />
            <EsgMetric
              label="Véhicules Utilisés"
              value={summary.vehicles_used}
              unit="camions"
              icon="🚛"
            />
          </SimpleGrid>
        </CardBody>
      </CardRoot>
    </Container>
  );
};

// Reusing sub-components
const StatCard = ({ icon, label, value, unit, color }: any) => (
  <CardRoot
    borderRadius="xl"
    bg="bg.panel"
    borderColor="border.subtle"
    boxShadow="sm"
  >
    <CardBody>
      <Flex justify="space-between" align="start">
        <Box>
          <Text fontSize="sm" color="fg.muted" fontWeight="medium" mb={1}>
            {label}
          </Text>
          <Flex align="baseline" gap={1}>
            <Text fontSize="3xl" fontWeight="bold" color="fg.default">
              {value}
            </Text>
            {unit && (
              <Text fontSize="sm" color="fg.muted">
                {unit}
              </Text>
            )}
          </Flex>
        </Box>
        <Box
          p={3}
          bg={`${color}.50`}
          _dark={{ bg: `${color}.900` }}
          borderRadius="xl"
        >
          <Icon
            as={icon}
            boxSize={5}
            color={`${color}.600`}
            _dark={{ color: `${color}.200` }}
          />
        </Box>
      </Flex>
    </CardBody>
  </CardRoot>
);

const EsgMetric = ({ label, value, unit, icon }: any) => (
  <Box>
    <Text fontSize="sm" opacity={0.8} mb={1} fontWeight="medium">
      {label}
    </Text>
    <Flex align="center" gap={2}>
      {icon && <Text fontSize="2xl">{icon}</Text>}
      <Text fontSize="4xl" fontWeight="extrabold" letterSpacing="tight">
        {value}
      </Text>
      <Text fontSize="lg" opacity={0.8} mt={2}>
        {unit}
      </Text>
    </Flex>
  </Box>
);

export default DashboardPage;
