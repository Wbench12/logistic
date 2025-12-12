import {
  Badge,
  Box,
  Button,
  CardBody,
  CardRoot,
  Container,
  chakra,
  DialogBackdrop,
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogPositioner,
  DialogRoot,
  Flex,
  Heading,
  Icon,
  Input,
  InputElement,
  InputGroup,
  MenuArrow,
  MenuContent,
  MenuItem,
  MenuPositioner,
  MenuRoot,
  MenuTrigger,
  SimpleGrid,
  Spinner,
  Stack,
  Text,
  useDisclosure,
} from "@chakra-ui/react";
import { keyframes } from "@emotion/react";
import type React from "react";
import { useMemo, useState } from "react";
import {
  FiCalendar,
  FiCheckCircle,
  FiClock,
  FiEdit2,
  FiMoreVertical,
  FiPlus,
  FiSearch,
  FiTrash2,
  FiTrendingDown,
  FiZap,
} from "react-icons/fi";
import { toaster } from "@/components/ui/toaster";

const cargoCategories = {
  a01_produits_frais: "Produits Frais",
  a02_produits_surgeles: "Produits Surgelés",
  b01_materiaux_vrac: "Matériaux en Vrac",
  b02_materiaux_solides: "Matériaux Solides",
  i01_produits_finis: "Produits Finis",
  c01_chimiques_liquides: "Produits Chimiques Liquides",
} as const;

const materialTypes = ["solide", "liquide", "gaz"] as const;

type TripStatus = "planned" | "in_progress" | "completed" | "cancelled";
type CargoCategoryKey = keyof typeof cargoCategories;

type MaterialType = (typeof materialTypes)[number];

interface Trip {
  id: string;
  departure_point: string;
  arrival_point: string;
  departure_datetime: string;
  arrival_datetime_planned: string;
  vehicle_id: string;
  driver_name: string;
  cargo_category: CargoCategoryKey;
  material_type: MaterialType;
  cargo_weight_kg: number;
  status: TripStatus;
}

interface TripFormState {
  departure_point: string;
  arrival_point: string;
  departure_datetime: string;
  arrival_datetime_planned: string;
  vehicle_id: string;
  driver_name: string;
  cargo_category: CargoCategoryKey;
  material_type: MaterialType;
  cargo_weight_kg: string;
  status: TripStatus;
}

interface OptimizationResult {
  status: string;
  batch_id: string;
  total_trips: number;
  km_saved: number;
  fuel_saved_liters: number;
  vehicles_used: number;
}

const statusConfig: Record<TripStatus, { label: string; color: string }> = {
  planned: { label: "Planifié", color: "purple" },
  in_progress: { label: "En Cours", color: "blue" },
  completed: { label: "Terminé", color: "green" },
  cancelled: { label: "Annulé", color: "red" },
};

const StyledSelect = chakra("select");

const FieldGroup = ({
  label,
  helper,
  required,
  children,
}: {
  label: string;
  helper?: string;
  required?: boolean;
  children: React.ReactNode;
}) => (
  <Stack gap={1}>
    <chakra.label fontSize="sm" fontWeight="semibold">
      {label}
      {required && (
        <Text as="span" color="red.500" ml={1}>
          *
        </Text>
      )}
    </chakra.label>
    {children}
    {helper && (
      <Text fontSize="sm" color="gray.500">
        {helper}
      </Text>
    )}
  </Stack>
);

const TableRoot = chakra("table");
const TableHead = chakra("thead");
const TableBody = chakra("tbody");
const TableRow = chakra("tr");
const TableCell = chakra("td");
const TableHeadCell = chakra("th");

const progressAnimation = keyframes`
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
`;

const IndeterminateProgress = () => (
  <Box
    position="relative"
    overflow="hidden"
    height="8px"
    bg="orange.100"
    borderRadius="full"
  >
    <Box
      position="absolute"
      inset="0"
      bgGradient="linear(to-r, orange.400, orange.600)"
      width="40%"
      animation={`${progressAnimation} 1.2s ease-in-out infinite`}
    />
  </Box>
);

const TripManagementPage = () => {
  const { open: addDialogOpen, onOpen, onClose } = useDisclosure();
  const {
    open: optimizeDialogOpen,
    onOpen: onOptimizeOpen,
    onClose: onOptimizeClose,
  } = useDisclosure();

  const [trips, setTrips] = useState<Trip[]>([
    {
      id: "TR-001",
      departure_point: "Oran",
      arrival_point: "Alger",
      departure_datetime: "2025-01-10T08:00",
      arrival_datetime_planned: "2025-01-10T16:00",
      vehicle_id: "V-001",
      driver_name: "Ahmed B.",
      cargo_category: "a01_produits_frais",
      material_type: "solide",
      cargo_weight_kg: 8000,
      status: "planned",
    },
    {
      id: "TR-002",
      departure_point: "Constantine",
      arrival_point: "Annaba",
      departure_datetime: "2025-01-10T09:30",
      arrival_datetime_planned: "2025-01-10T14:00",
      vehicle_id: "V-002",
      driver_name: "Mohamed K.",
      cargo_category: "b01_materiaux_vrac",
      material_type: "solide",
      cargo_weight_kg: 12000,
      status: "planned",
    },
    {
      id: "TR-003",
      departure_point: "Alger",
      arrival_point: "Oran",
      departure_datetime: "2025-01-10T07:15",
      arrival_datetime_planned: "2025-01-10T15:00",
      vehicle_id: "V-003",
      driver_name: "Karim M.",
      cargo_category: "i01_produits_finis",
      material_type: "solide",
      cargo_weight_kg: 5000,
      status: "in_progress",
    },
  ]);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState<"all" | TripStatus>("all");
  const [optimizing, setOptimizing] = useState(false);
  const [optimizationResult, setOptimizationResult] =
    useState<OptimizationResult | null>(null);
  const [editingTrip, setEditingTrip] = useState<Trip | null>(null);
  const [formData, setFormData] = useState<TripFormState>({
    departure_point: "",
    arrival_point: "",
    departure_datetime: "",
    arrival_datetime_planned: "",
    vehicle_id: "",
    driver_name: "",
    cargo_category: "a01_produits_frais",
    material_type: "solide",
    cargo_weight_kg: "",
    status: "planned",
  });

  const filteredTrips = useMemo(() => {
    return trips.filter((trip) => {
      const term = searchTerm.toLowerCase();
      const matchesSearch =
        trip.id.toLowerCase().includes(term) ||
        trip.departure_point.toLowerCase().includes(term) ||
        trip.arrival_point.toLowerCase().includes(term);
      const matchesStatus =
        filterStatus === "all" || trip.status === filterStatus;
      return matchesSearch && matchesStatus;
    });
  }, [trips, searchTerm, filterStatus]);

  const plannedTrips = useMemo(
    () => trips.filter((trip) => trip.status === "planned"),
    [trips]
  );

  const stats = useMemo(
    () => ({
      total: trips.length,
      planned: trips.filter((trip) => trip.status === "planned").length,
      in_progress: trips.filter((trip) => trip.status === "in_progress").length,
      completed: trips.filter((trip) => trip.status === "completed").length,
    }),
    [trips]
  );

  const resetForm = () => {
    setEditingTrip(null);
    setFormData({
      departure_point: "",
      arrival_point: "",
      departure_datetime: "",
      arrival_datetime_planned: "",
      vehicle_id: "",
      driver_name: "",
      cargo_category: "a01_produits_frais",
      material_type: "solide",
      cargo_weight_kg: "",
      status: "planned",
    });
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleOptimize = () => {
    setOptimizing(true);

    setTimeout(() => {
      const mockResult: OptimizationResult = {
        status: "SUCCESS",
        batch_id: "batch-123",
        total_trips: plannedTrips.length,
        km_saved: 450.5,
        fuel_saved_liters: 135.15,
        vehicles_used: Math.max(1, Math.round(plannedTrips.length / 2)),
      };

      setOptimizationResult(mockResult);
      setOptimizing(false);
      onOptimizeClose();

      toaster.success({
        title: "Optimisation réussie",
        description: `${mockResult.km_saved} km économisés, ${mockResult.fuel_saved_liters} L carburant économisés`,
        meta: { color: "green.solid", closable: true },
      });
    }, 3000);
  };

  const handleAddOrUpdateTrip = () => {
    if (
      !formData.departure_point ||
      !formData.arrival_point ||
      !formData.departure_datetime ||
      !formData.arrival_datetime_planned ||
      !formData.vehicle_id
    ) {
      toaster.warning({
        title: "Champs manquants",
        description: "Renseignez les champs obligatoires avant de continuer.",
        meta: { color: "orange.solid", closable: true },
      });
      return;
    }

    const normalizedData = {
      departure_point: formData.departure_point,
      arrival_point: formData.arrival_point,
      departure_datetime: formData.departure_datetime,
      arrival_datetime_planned: formData.arrival_datetime_planned,
      vehicle_id: formData.vehicle_id,
      driver_name: formData.driver_name,
      cargo_category: formData.cargo_category,
      material_type: formData.material_type,
      cargo_weight_kg: Number(formData.cargo_weight_kg) || 0,
      status: formData.status,
    };

    if (editingTrip) {
      setTrips((prev) =>
        prev.map((trip) =>
          trip.id === editingTrip.id ? { ...trip, ...normalizedData } : trip
        )
      );
      toaster.success({
        title: "Trajet mis à jour",
        description: "Les informations du trajet ont été enregistrées.",
        meta: { color: "blue.solid", closable: true },
      });
    } else {
      const newTrip: Trip = {
        id: generateTripId(trips.length + 1),
        ...normalizedData,
      };
      setTrips((prev) => [...prev, newTrip]);
      toaster.success({
        title: "Trajet ajouté",
        description: "Le nouveau trajet a été créé avec succès.",
        meta: { color: "blue.solid", closable: true },
      });
    }

    handleClose();
  };

  const handleEdit = (trip: Trip) => {
    setEditingTrip(trip);
    setFormData({
      departure_point: trip.departure_point,
      arrival_point: trip.arrival_point,
      departure_datetime: trip.departure_datetime,
      arrival_datetime_planned: trip.arrival_datetime_planned,
      vehicle_id: trip.vehicle_id,
      driver_name: trip.driver_name,
      cargo_category: trip.cargo_category,
      material_type: trip.material_type,
      cargo_weight_kg: String(trip.cargo_weight_kg),
      status: trip.status,
    });
    onOpen();
  };

  const handleDelete = (tripId: string) => {
    setTrips((prev) => prev.filter((trip) => trip.id !== tripId));
    toaster.success({
      title: "Trajet supprimé",
      description: "Le trajet a été retiré de la planification.",
      meta: { color: "red.solid", closable: true },
    });
  };

  return (
    <Container maxW="full" py={8} px={6}>
      <Flex justifyContent="space-between" alignItems="center" mb={8}>
        <Box>
          <Heading
            size="xl"
            mb={2}
            bgGradient="linear(to-r, blue.400, cyan.500)"
            bgClip="text"
          >
            Gestion des Trajets
          </Heading>
          <Text color="gray.600">Planifiez et optimisez vos trajets</Text>
        </Box>
        <Flex gap={3} flexWrap="wrap" justifyContent="flex-end">
          <Button
            colorScheme="orange"
            size="lg"
            onClick={onOptimizeOpen}
            borderRadius="xl"
            disabled={plannedTrips.length === 0}
          >
            <Icon as={FiZap} boxSize={5} mr={2} />
            Optimiser
          </Button>
          <Button
            colorScheme="blue"
            size="lg"
            onClick={onOpen}
            borderRadius="xl"
          >
            <Icon as={FiPlus} boxSize={5} mr={2} />
            Ajouter un Trajet
          </Button>
        </Flex>
      </Flex>

      {optimizationResult && (
        <CardRoot
          variant="elevated"
          borderRadius="xl"
          mb={6}
          bg="orange.50"
          borderWidth={2}
          borderColor="orange.200"
        >
          <CardBody p={6}>
            <Flex alignItems="center" mb={4} gap={3}>
              <Icon as={FiZap} boxSize={6} color="orange.600" />
              <Heading size="md" color="orange.800">
                Résultats d'Optimisation
              </Heading>
              <Badge ml="auto" colorScheme="green" fontSize="sm" px={3} py={1}>
                Complété
              </Badge>
            </Flex>

            <SimpleGrid columns={{ base: 1, md: 4 }} gap={4}>
              <StatCard
                label="Trajets Traités"
                value={optimizationResult.total_trips}
                icon={FiCalendar}
                color="orange.500"
              />
              <StatCard
                label="KM Économisés"
                value={`${optimizationResult.km_saved} km`}
                icon={FiTrendingDown}
                color="green.500"
              />
              <StatCard
                label="Carburant Sauvé"
                value={`${optimizationResult.fuel_saved_liters} L`}
                icon={FiCheckCircle}
                color="green.500"
              />
              <StatCard
                label="Véhicules Utilisés"
                value={optimizationResult.vehicles_used}
                icon={FiZap}
                color="orange.500"
              />
            </SimpleGrid>
          </CardBody>
        </CardRoot>
      )}

      <SimpleGrid columns={{ base: 1, md: 4 }} gap={6} mb={8}>
        <StatCard
          label="Total Trajets"
          value={stats.total}
          icon={FiCalendar}
          color="blue.500"
        />
        <StatCard
          label="Planifiés"
          value={stats.planned}
          icon={FiClock}
          color="purple.500"
        />
        <StatCard
          label="En Cours"
          value={stats.in_progress}
          icon={FiCheckCircle}
          color="blue.500"
        />
        <StatCard
          label="Terminés"
          value={stats.completed}
          icon={FiTrendingDown}
          color="green.500"
        />
      </SimpleGrid>

      <CardRoot variant="elevated" borderRadius="xl" mb={6}>
        <CardBody>
          <Flex gap={4} flexWrap="wrap">
            <InputGroup
              flex={1}
              minW="240px"
              startElement={
                <InputElement pointerEvents="none">
                  <Icon as={FiSearch} color="gray.500" />
                </InputElement>
              }
            >
              <Input
                placeholder="Rechercher un trajet (ID, ville...)"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
              />
            </InputGroup>
            <StyledSelect
              maxW="220px"
              value={filterStatus}
              onChange={(event) =>
                setFilterStatus(event.target.value as TripStatus | "all")
              }
              borderWidth="1px"
              borderColor="gray.200"
              borderRadius="md"
              bg="white"
              px={3}
              py={2}
              _focusVisible={{
                outline: "2px solid",
                outlineColor: "purple.500",
              }}
            >
              <option value="all">Tous les statuts</option>
              <option value="planned">Planifié</option>
              <option value="in_progress">En Cours</option>
              <option value="completed">Terminé</option>
              <option value="cancelled">Annulé</option>
            </StyledSelect>
          </Flex>
        </CardBody>
      </CardRoot>

      <CardRoot variant="elevated" borderRadius="xl">
        <CardBody p={0}>
          <Box overflowX="auto">
            <TableRoot
              width="100%"
              borderCollapse="separate"
              borderSpacing="0 12px"
            >
              <TableHead>
                <TableRow>
                  {[
                    "ID",
                    "Départ → Arrivée",
                    "Date/Heure",
                    "Véhicule",
                    "Chauffeur",
                    "Cargo",
                    "Poids",
                    "Statut",
                    "Actions",
                  ].map((heading) => (
                    <TableHeadCell
                      key={heading}
                      textAlign="left"
                      fontSize="sm"
                      color="gray.500"
                      px={3}
                      py={3}
                    >
                      {heading}
                    </TableHeadCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredTrips.map((trip) => (
                  <TableRow
                    key={trip.id}
                    position="relative"
                    bg="white"
                    borderRadius="xl"
                    boxShadow="sm"
                    _hover={{ bg: "gray.50" }}
                  >
                    <TableCell fontWeight="medium" px={3} py={4}>
                      {trip.id}
                    </TableCell>
                    <TableCell px={3} py={4}>
                      <Text fontSize="sm" fontWeight="medium">
                        {trip.departure_point}
                      </Text>
                      <Text fontSize="sm" color="gray.500">
                        ↓
                      </Text>
                      <Text fontSize="sm" fontWeight="medium">
                        {trip.arrival_point}
                      </Text>
                    </TableCell>
                    <TableCell px={3} py={4}>
                      <Text fontSize="sm">
                        {new Date(trip.departure_datetime).toLocaleDateString(
                          "fr-FR"
                        )}
                      </Text>
                      <Text fontSize="xs" color="gray.500">
                        {new Date(trip.departure_datetime).toLocaleTimeString(
                          "fr-FR",
                          {
                            hour: "2-digit",
                            minute: "2-digit",
                          }
                        )}
                      </Text>
                    </TableCell>
                    <TableCell px={3} py={4}>
                      <Badge colorScheme="gray" variant="subtle">
                        {trip.vehicle_id}
                      </Badge>
                    </TableCell>
                    <TableCell px={3} py={4}>
                      {trip.driver_name || "Non assigné"}
                    </TableCell>
                    <TableCell px={3} py={4}>
                      <Text fontSize="sm">
                        {cargoCategories[trip.cargo_category]}
                      </Text>
                      <Badge size="sm" colorScheme="gray">
                        {trip.material_type}
                      </Badge>
                    </TableCell>
                    <TableCell px={3} py={4}>
                      {(trip.cargo_weight_kg / 1000).toFixed(1)} T
                    </TableCell>
                    <TableCell px={3} py={4}>
                      <Badge colorScheme={statusConfig[trip.status].color}>
                        {statusConfig[trip.status].label}
                      </Badge>
                    </TableCell>
                    <TableCell px={3} py={4} textAlign="right">
                      <MenuRoot>
                        <MenuTrigger asChild>
                          <chakra.button
                            aria-label="Ouvrir les actions"
                            bg="transparent"
                            _hover={{ bg: "gray.100" }}
                            p={2}
                            borderRadius="full"
                            cursor="pointer"
                            display="inline-flex"
                            alignItems="center"
                            justifyContent="center"
                          >
                            <Icon as={FiMoreVertical} boxSize={5} />
                          </chakra.button>
                        </MenuTrigger>
                        <MenuPositioner>
                          <MenuContent borderRadius="lg" minW="220px">
                            <MenuArrow />
                            <MenuItem
                              value="edit"
                              display="flex"
                              alignItems="center"
                              gap={2}
                              onClick={() => handleEdit(trip)}
                            >
                              <Icon as={FiEdit2} boxSize={4} />
                              Modifier
                            </MenuItem>
                            <MenuItem
                              value="delete"
                              display="flex"
                              alignItems="center"
                              gap={2}
                              color="red.500"
                              onClick={() => handleDelete(trip.id)}
                            >
                              <Icon as={FiTrash2} boxSize={4} />
                              Supprimer
                            </MenuItem>
                          </MenuContent>
                        </MenuPositioner>
                      </MenuRoot>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </TableRoot>
          </Box>
        </CardBody>
      </CardRoot>

      <DialogRoot
        open={optimizeDialogOpen}
        onOpenChange={(open) => (open ? onOptimizeOpen() : onOptimizeClose())}
      >
        <DialogBackdrop />
        <DialogPositioner>
          <DialogContent borderRadius="xl" maxW="640px">
            <DialogHeader>
              <Flex alignItems="center" gap={3}>
                <Icon as={FiZap} color="orange.500" />
                <Text fontSize="lg" fontWeight="semibold">
                  Optimisation des Trajets
                </Text>
              </Flex>
              <DialogCloseTrigger asChild>
                <Button variant="ghost" size="sm">
                  Fermer
                </Button>
              </DialogCloseTrigger>
            </DialogHeader>
            <DialogBody pb={6}>
              {optimizing ? (
                <Flex direction="column" alignItems="center" py={8} w="full">
                  <Spinner size="xl" color="orange.500" mb={4} />
                  <Text fontSize="lg" fontWeight="medium" mb={2}>
                    Optimisation en cours...
                  </Text>
                  <Text color="gray.600" textAlign="center">
                    L'algorithme CP-SAT analyse {plannedTrips.length} trajets
                    pour minimiser les retours à vide.
                  </Text>
                  <Box w="full" mt={6}>
                    <IndeterminateProgress />
                  </Box>
                </Flex>
              ) : (
                <>
                  <Text mb={4} color="gray.700">
                    Cette opération optimisera tous les trajets planifiés
                    d'aujourd'hui afin de minimiser les retours à vide.
                  </Text>
                  <CardRoot variant="outline" borderRadius="lg" mb={4}>
                    <CardBody>
                      <Heading size="sm" mb={3}>
                        Détails de l'optimisation
                      </Heading>
                      <SimpleGrid columns={2} gap={3}>
                        <Box>
                          <Text fontSize="sm" color="gray.600">
                            Trajets à optimiser
                          </Text>
                          <Text fontSize="xl" fontWeight="bold">
                            {plannedTrips.length}
                          </Text>
                        </Box>
                        <Box>
                          <Text fontSize="sm" color="gray.600">
                            Date cible
                          </Text>
                          <Text fontSize="xl" fontWeight="bold">
                            {new Date().toLocaleDateString("fr-FR")}
                          </Text>
                        </Box>
                      </SimpleGrid>
                    </CardBody>
                  </CardRoot>
                  <Box bg="blue.50" p={4} borderRadius="lg">
                    <Text fontSize="sm" color="blue.700">
                      <chakra.span fontWeight="bold">Objectif :</chakra.span>{" "}
                      Enchaîner les trajets compatibles pour réduire les retours
                      à vide.
                    </Text>
                  </Box>
                </>
              )}
            </DialogBody>
            {!optimizing && (
              <DialogFooter>
                <Button variant="ghost" mr={3} onClick={onOptimizeClose}>
                  Annuler
                </Button>
                <Button colorScheme="orange" onClick={handleOptimize}>
                  Lancer l'optimisation
                </Button>
              </DialogFooter>
            )}
          </DialogContent>
        </DialogPositioner>
      </DialogRoot>

      <DialogRoot
        open={addDialogOpen}
        onOpenChange={(open) => (open ? onOpen() : onClose())}
      >
        <DialogBackdrop />
        <DialogPositioner>
          <DialogContent borderRadius="xl" maxW="900px">
            <DialogHeader>
              <Text fontSize="lg" fontWeight="semibold">
                {editingTrip ? "Modifier le Trajet" : "Ajouter un Trajet"}
              </Text>
            </DialogHeader>
            <DialogBody pb={6}>
              <SimpleGrid columns={{ base: 1, md: 2 }} gap={6}>
                <FieldGroup label="Point de départ" required>
                  <Input
                    value={formData.departure_point}
                    onChange={(event) =>
                      setFormData((prev) => ({
                        ...prev,
                        departure_point: event.target.value,
                      }))
                    }
                  />
                </FieldGroup>
                <FieldGroup label="Point d'arrivée" required>
                  <Input
                    value={formData.arrival_point}
                    onChange={(event) =>
                      setFormData((prev) => ({
                        ...prev,
                        arrival_point: event.target.value,
                      }))
                    }
                  />
                </FieldGroup>
                <FieldGroup label="Départ (date & heure)" required>
                  <Input
                    type="datetime-local"
                    value={formData.departure_datetime}
                    onChange={(event) =>
                      setFormData((prev) => ({
                        ...prev,
                        departure_datetime: event.target.value,
                      }))
                    }
                  />
                </FieldGroup>
                <FieldGroup label="Arrivée prévue" required>
                  <Input
                    type="datetime-local"
                    value={formData.arrival_datetime_planned}
                    onChange={(event) =>
                      setFormData((prev) => ({
                        ...prev,
                        arrival_datetime_planned: event.target.value,
                      }))
                    }
                  />
                </FieldGroup>
                <FieldGroup label="Véhicule" required>
                  <Input
                    value={formData.vehicle_id}
                    onChange={(event) =>
                      setFormData((prev) => ({
                        ...prev,
                        vehicle_id: event.target.value,
                      }))
                    }
                    placeholder="V-001"
                  />
                </FieldGroup>
                <FieldGroup label="Chauffeur">
                  <Input
                    value={formData.driver_name}
                    onChange={(event) =>
                      setFormData((prev) => ({
                        ...prev,
                        driver_name: event.target.value,
                      }))
                    }
                    placeholder="Ahmed B."
                  />
                </FieldGroup>
                <FieldGroup label="Catégorie de cargo" required>
                  <StyledSelect
                    value={formData.cargo_category}
                    onChange={(event) =>
                      setFormData((prev) => ({
                        ...prev,
                        cargo_category: event.target.value as CargoCategoryKey,
                      }))
                    }
                    borderWidth="1px"
                    borderColor="gray.200"
                    borderRadius="md"
                    bg="white"
                    px={3}
                    py={2}
                    _focusVisible={{
                      outline: "2px solid",
                      outlineColor: "purple.500",
                    }}
                  >
                    {Object.entries(cargoCategories).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </StyledSelect>
                </FieldGroup>
                <FieldGroup label="Type de marchandise" required>
                  <StyledSelect
                    value={formData.material_type}
                    onChange={(event) =>
                      setFormData((prev) => ({
                        ...prev,
                        material_type: event.target.value as MaterialType,
                      }))
                    }
                    borderWidth="1px"
                    borderColor="gray.200"
                    borderRadius="md"
                    bg="white"
                    px={3}
                    py={2}
                    _focusVisible={{
                      outline: "2px solid",
                      outlineColor: "purple.500",
                    }}
                  >
                    {materialTypes.map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </StyledSelect>
                </FieldGroup>
                <FieldGroup label="Poids (kg)" required>
                  <Input
                    type="number"
                    value={formData.cargo_weight_kg}
                    onChange={(event) =>
                      setFormData((prev) => ({
                        ...prev,
                        cargo_weight_kg: event.target.value,
                      }))
                    }
                    placeholder="8000"
                  />
                </FieldGroup>
                <FieldGroup label="Statut" required>
                  <StyledSelect
                    value={formData.status}
                    onChange={(event) =>
                      setFormData((prev) => ({
                        ...prev,
                        status: event.target.value as TripStatus,
                      }))
                    }
                    borderWidth="1px"
                    borderColor="gray.200"
                    borderRadius="md"
                    bg="white"
                    px={3}
                    py={2}
                    _focusVisible={{
                      outline: "2px solid",
                      outlineColor: "purple.500",
                    }}
                  >
                    <option value="planned">Planifié</option>
                    <option value="in_progress">En Cours</option>
                    <option value="completed">Terminé</option>
                    <option value="cancelled">Annulé</option>
                  </StyledSelect>
                </FieldGroup>
              </SimpleGrid>
            </DialogBody>
            <DialogFooter>
              <Button variant="ghost" mr={3} onClick={handleClose}>
                Annuler
              </Button>
              <Button colorScheme="blue" onClick={handleAddOrUpdateTrip}>
                {editingTrip ? "Mettre à jour" : "Ajouter"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </DialogPositioner>
      </DialogRoot>
    </Container>
  );
};

interface StatCardProps {
  label: string;
  value: number | string;
  icon: React.ComponentType;
  color: string;
}

const StatCard = ({ label, value, icon, color }: StatCardProps) => {
  const accentColor = color.includes(".") ? color.split(".")[0] : color;

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
      </CardBody>
    </CardRoot>
  );
};

function generateTripId(index: number) {
  return `TR-${String(index).padStart(3, "0")}`;
}

export default TripManagementPage;
