import {
  Box,
  Button,
  Badge,
  CardBody,
  CardRoot,
  Container,
  Flex,
  Heading,
  HStack,
  Icon,
  IconButton,
  Input,
  Separator,
  SimpleGrid,
  Stack,
  Table,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form"; // Restored this
import {
  FiCalendar,
  FiCheckCircle,
  FiClock,
  FiUpload,
  FiMap,
  FiList,
  FiZap,
  FiPlus, // Added Plus icon
} from "react-icons/fi";

// Import Standard Service for creating single trips
import { TripsService, type TripCreate, type ApiError } from "@/client";
// Import Extended Service for complex features (Upload, Optimize, Map Data)
import {
  ExtendedTripsService,
  type UploadResponse,
  type OptimizationResponse,
} from "@/client/services/ExtendedTripsService";

import {
  DialogActionTrigger,
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field } from "@/components/ui/field"; // Restored Field
import { SkeletonText } from "@/components/ui/skeleton";
import { Toaster, toaster } from "@/components/ui/toaster";
import TripMap from "./TripMap";
import { handleError } from "@/utils";
import { useCompany } from "@/hooks/useCompany";

const getToday = () => new Date().toISOString().split("T")[0];

// Configuration for the form
const cargoCategories = {
  a01_produits_frais: "Produits Frais",
  b01_materiaux_vrac: "Matériaux Vrac",
  i01_produits_finis: "Produits Finis",
};

const TripManagementPage = () => {
  const queryClient = useQueryClient();
  const { company } = useCompany();
  const [selectedDate, setSelectedDate] = useState(getToday());
  const [viewMode, setViewMode] = useState<"list" | "map">("list");

  // Modal States
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isAddOpen, setIsAddOpen] = useState(false); // State for Add Trip Modal
  const [file, setFile] = useState<File | null>(null);

  // --- Form Hook for Single Trip ---
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<TripCreate>({
    defaultValues: {
      status: "planifie",
      cargo_category: "a01_produits_frais",
      material_type: "solide",
      departure_datetime: `${getToday()}T08:00`, // Default start time
      arrival_datetime_planned: `${getToday()}T12:00`,
    },
  });

  const shouldFetch = !!company;

  // --- Queries ---
  const { data: tripsData, isLoading: isLoadingList } = useQuery({
    queryKey: ["trips", selectedDate],
    queryFn: () => ExtendedTripsService.getTripsByDate(selectedDate),
    enabled: shouldFetch,
  });

  const { data: mapData, isLoading: isLoadingMap } = useQuery({
    queryKey: ["tripsMap", selectedDate],
    queryFn: () => ExtendedTripsService.getMapData(selectedDate),
    enabled: shouldFetch && viewMode === "map",
  });

  const { data: kpiData } = useQuery({
    queryKey: ["tripsKPI", selectedDate],
    queryFn: () => ExtendedTripsService.getKPIs(selectedDate),
    enabled: shouldFetch,
  });

  // --- Mutations ---

  // 1. Create Single Trip
  const createTripMutation = useMutation({
    mutationFn: (data: TripCreate) =>
      TripsService.createTrip({ requestBody: data }),
    onSuccess: () => {
      toaster.success({
        title: "Trajet ajouté",
        description: "Le trajet a été planifié avec succès.",
      });
      setIsAddOpen(false);
      reset(); // Clear form
      queryClient.invalidateQueries({ queryKey: ["trips"] });
      queryClient.invalidateQueries({ queryKey: ["tripsMap"] });
      queryClient.invalidateQueries({ queryKey: ["tripsKPI"] });
    },
    onError: (err: ApiError) => handleError(err),
  });

  // 2. Upload File
  const uploadMutation = useMutation({
    mutationFn: (formData: FormData) =>
      ExtendedTripsService.uploadTrips(formData),
    onSuccess: (res: UploadResponse) => {
      toaster.success({
        title: "Import réussi",
        description: `${res.summary.successful} trajets importés.`,
      });
      setIsUploadOpen(false);
      setFile(null);
      queryClient.invalidateQueries({ queryKey: ["trips"] });
      queryClient.invalidateQueries({ queryKey: ["tripsMap"] });
      queryClient.invalidateQueries({ queryKey: ["tripsKPI"] });
    },
    onError: (err: any) => handleError(err),
  });

  // 3. Optimize
  const optimizeMutation = useMutation({
    mutationFn: () => ExtendedTripsService.optimize(selectedDate),
    onSuccess: (res: OptimizationResponse) => {
      toaster.success({
        title: "Optimisation lancée",
        description: `Batch ID: ${res.details.trips_optimized} trajets traités.`,
      });
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["trips"] });
        queryClient.invalidateQueries({ queryKey: ["tripsMap"] });
      }, 2000);
    },
    onError: (err: any) => handleError(err),
  });

  // --- Handlers ---

  const handleCreateSubmit = (data: TripCreate) => {
    // Ensure numbers are numbers
    const payload: any = {
      ...data,
      cargo_weight_kg: Number(data.cargo_weight_kg),
    };

    if (!payload.vehicle_id) {
      payload.vehicle_id = null;
    }
    createTripMutation.mutate(payload);
  };

  const handleUploadSubmit = () => {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    formData.append("file_type", file.name.endsWith(".xlsx") ? "excel" : "csv");
    uploadMutation.mutate(formData);
  };

  // Handle clicking on the map
  const handleMapClick = (lat: number, lng: number) => {
    // For now, simply open the modal.
    // In the future, you can setValues for coordinates if your API supports it.
    toaster.info({
      title: "Localisation",
      description: `${lat.toFixed(4)}, ${lng.toFixed(4)}`,
    });
    setIsAddOpen(true);
  };

  const summary = kpiData?.summary || { trips_contributed: 0 };
  const savings = kpiData?.savings || { km_saved: 0, fuel_saved_liters: 0 };

  return (
    <Container maxW="full" py={8} px={{ base: 4, md: 8 }}>
      <Toaster />

      <Flex
        justify="space-between"
        align={{ base: "start", md: "center" }}
        direction={{ base: "column", md: "row" }}
        gap={4}
        mb={8}
      >
        <Box>
          <Heading size="2xl" mb={2} color="fg.default">
            Planification
          </Heading>
          <Text color="fg.muted" fontSize="lg">
            Gérez vos trajets et optimisez les tournées.
          </Text>
        </Box>

        <Stack direction={{ base: "column", md: "row" }} gap={3} align="center">
          <Input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            w="auto"
            bg="bg.panel"
            borderColor="border.subtle"
          />

          <HStack
            bg="bg.panel"
            p={1}
            borderRadius="lg"
            borderWidth="1px"
            borderColor="border.subtle"
          >
            <IconButton
              variant={viewMode === "list" ? "solid" : "ghost"}
              colorPalette="brand"
              onClick={() => setViewMode("list")}
              aria-label="List View"
            >
              <FiList />
            </IconButton>
            <IconButton
              variant={viewMode === "map" ? "solid" : "ghost"}
              colorPalette="brand"
              onClick={() => setViewMode("map")}
              aria-label="Map View"
            >
              <FiMap />
            </IconButton>
          </HStack>

          <Separator
            orientation="vertical"
            h="8"
            mx={2}
            display={{ base: "none", md: "block" }}
          />

          {/* New Trip Button */}
          <Button colorPalette="brand" onClick={() => setIsAddOpen(true)}>
            <FiPlus /> Nouveau Trajet
          </Button>

          <Button
            colorPalette="orange"
            variant="surface"
            onClick={() => optimizeMutation.mutate()}
            loading={optimizeMutation.isPending}
            disabled={!tripsData?.count}
          >
            <FiZap /> Optimiser
          </Button>
          <Button variant="outline" onClick={() => setIsUploadOpen(true)}>
            <FiUpload /> Import Excel
          </Button>
        </Stack>
      </Flex>

      {/* KPI Section */}
      <SimpleGrid columns={{ base: 1, md: 3 }} gap={6} mb={8}>
        <StatCard
          label="Total Trajets"
          value={summary.trips_contributed}
          icon={FiCalendar}
          color="blue"
        />
        <StatCard
          label="KM Économisés"
          value={savings.km_saved?.toFixed(1) || 0}
          unit="km"
          icon={FiCheckCircle}
          color="green"
        />
        <StatCard
          label="Carburant Sauvé"
          value={savings.fuel_saved_liters?.toFixed(1) || 0}
          unit="L"
          icon={FiClock}
          color="purple"
        />
      </SimpleGrid>

      <CardRoot
        variant="elevated"
        borderRadius="xl"
        bg="bg.panel"
        boxShadow="sm"
      >
        <CardBody p={viewMode === "map" ? 0 : 6}>
          {viewMode === "map" ? (
            <Box position="relative" h="600px" w="full">
              {isLoadingMap ? (
                <Flex h="full" align="center" justify="center">
                  <Text>Chargement de la carte...</Text>
                </Flex>
              ) : (
                <TripMap
                  data={mapData}
                  onMapClick={handleMapClick} // Pass the handler here
                />
              )}
            </Box>
          ) : (
            <Box overflowX="auto">
              <Table.Root interactive size="lg">
                <Table.Header bg="bg.subtle">
                  <Table.Row>
                    <Table.ColumnHeader>Départ</Table.ColumnHeader>
                    <Table.ColumnHeader>Arrivée</Table.ColumnHeader>
                    <Table.ColumnHeader>Date/Heure</Table.ColumnHeader>
                    <Table.ColumnHeader>Cargaison</Table.ColumnHeader>
                    <Table.ColumnHeader>Statut</Table.ColumnHeader>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  {isLoadingList ? (
                    <Table.Row>
                      <Table.Cell colSpan={5}>
                        <SkeletonText noOfLines={3} />
                      </Table.Cell>
                    </Table.Row>
                  ) : tripsData?.data && tripsData.data.length > 0 ? (
                    tripsData.data.map((trip: any) => (
                      <Table.Row key={trip.id}>
                        <Table.Cell fontWeight="medium">
                          {trip.departure_point}
                        </Table.Cell>
                        <Table.Cell>{trip.arrival_point}</Table.Cell>
                        <Table.Cell color="fg.muted">
                          {new Date(trip.departure_datetime).toLocaleString()}
                        </Table.Cell>
                        <Table.Cell>
                          {trip.cargo_category} ({trip.cargo_weight_kg} kg)
                        </Table.Cell>
                        <Table.Cell>
                          <StatusBadge status={trip.status} />
                        </Table.Cell>
                      </Table.Row>
                    ))
                  ) : (
                    <Table.Row>
                      <Table.Cell
                        colSpan={5}
                        textAlign="center"
                        py={8}
                        color="fg.muted"
                      >
                        {company
                          ? "Aucun trajet pour cette date."
                          : "Veuillez d'abord configurer votre entreprise."}
                      </Table.Cell>
                    </Table.Row>
                  )}
                </Table.Body>
              </Table.Root>
            </Box>
          )}
        </CardBody>
      </CardRoot>

      {/* --- MODAL 1: Add New Trip --- */}
      <DialogRoot
        open={isAddOpen}
        onOpenChange={(e) => setIsAddOpen(e.open)}
        size="lg"
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ajouter un Trajet Simple</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Stack
              gap={4}
              as="form"
              id="create-trip-form"
              onSubmit={handleSubmit(handleCreateSubmit)}
            >
              <SimpleGrid columns={2} gap={4}>
                <Field
                  label="Point de Départ"
                  required
                  invalid={!!errors.departure_point}
                >
                  <Input
                    {...register("departure_point", { required: "Requis" })}
                    placeholder="Ex: Alger"
                  />
                </Field>
                <Field
                  label="Point d'Arrivée"
                  required
                  invalid={!!errors.arrival_point}
                >
                  <Input
                    {...register("arrival_point", { required: "Requis" })}
                    placeholder="Ex: Oran"
                  />
                </Field>
              </SimpleGrid>

              <SimpleGrid columns={2} gap={4}>
                <Field label="Départ Prévu" required>
                  <Input
                    type="datetime-local"
                    {...register("departure_datetime", { required: true })}
                  />
                </Field>
                <Field label="Arrivée Estimée" required>
                  <Input
                    type="datetime-local"
                    {...register("arrival_datetime_planned", {
                      required: true,
                    })}
                  />
                </Field>
              </SimpleGrid>

              <SimpleGrid columns={2} gap={4}>
                <Field label="Véhicule ID (Optionnel)">
                  <Input {...register("vehicle_id")} placeholder="Ex: V-001" />
                </Field>
                <Field label="Chauffeur (Optionnel)">
                  <Input
                    {...register("driver_name")}
                    placeholder="Nom du chauffeur"
                  />
                </Field>
              </SimpleGrid>

              <SimpleGrid columns={2} gap={4}>
                <Field label="Type Cargaison" required>
                  <select
                    {...register("cargo_category")}
                    style={{
                      width: "100%",
                      padding: "8px",
                      border: "1px solid #ccc",
                      borderRadius: "4px",
                    }}
                  >
                    {Object.entries(cargoCategories).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Poids (kg)" required>
                  <Input
                    type="number"
                    {...register("cargo_weight_kg", { required: true })}
                  />
                </Field>
              </SimpleGrid>

              {/* Hidden Defaults */}
              <input
                type="hidden"
                {...register("material_type")}
                value="solide"
              />
              <input type="hidden" {...register("status")} value="planifie" />
            </Stack>
          </DialogBody>
          <DialogFooter>
            <DialogActionTrigger asChild>
              <Button variant="ghost">Annuler</Button>
            </DialogActionTrigger>
            <Button
              type="submit"
              form="create-trip-form"
              loading={createTripMutation.isPending}
              colorPalette="brand"
            >
              Créer le trajet
            </Button>
          </DialogFooter>
          <DialogCloseTrigger />
        </DialogContent>
      </DialogRoot>

      {/* --- MODAL 2: Upload --- */}
      <DialogRoot
        open={isUploadOpen}
        onOpenChange={(e) => setIsUploadOpen(e.open)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Importer des trajets (CSV)</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <VStack gap={4}>
              <Text fontSize="sm" color="fg.muted">
                Format requis: CSV ou Excel
              </Text>
              <Box
                borderWidth="2px"
                borderStyle="dashed"
                borderColor="border.subtle"
                borderRadius="xl"
                p={8}
                textAlign="center"
                w="full"
                bg="bg.subtle"
              >
                <Input
                  type="file"
                  accept=".csv, .xlsx"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  pt={1}
                />
              </Box>
            </VStack>
          </DialogBody>
          <DialogFooter>
            <DialogActionTrigger asChild>
              <Button variant="ghost">Annuler</Button>
            </DialogActionTrigger>
            <Button
              onClick={handleUploadSubmit}
              loading={uploadMutation.isPending}
              disabled={!file}
              colorPalette="brand"
            >
              Uploader
            </Button>
          </DialogFooter>
          <DialogCloseTrigger />
        </DialogContent>
      </DialogRoot>
    </Container>
  );
};

const StatCard = ({ label, value, unit, color, icon: IconComp }: any) => (
  <CardRoot
    borderRadius="xl"
    borderLeft="4px solid"
    borderColor={`${color}.500`}
    bg="bg.panel"
    boxShadow="sm"
  >
    <CardBody>
      <Flex justify="space-between" align="center">
        <Box>
          <Text fontSize="sm" color="fg.muted" fontWeight="medium">
            {label}
          </Text>
          <HStack align="baseline" gap={1}>
            <Text fontSize="2xl" fontWeight="bold" color="fg.default">
              {value}
            </Text>
            {unit && (
              <Text fontSize="sm" color="fg.muted">
                {unit}
              </Text>
            )}
          </HStack>
        </Box>
        <Box
          p={2}
          bg={`${color}.50`}
          _dark={{ bg: `${color}.900` }}
          borderRadius="lg"
        >
          <Icon as={IconComp} size="lg" color={`${color}.500`} />
        </Box>
      </Flex>
    </CardBody>
  </CardRoot>
);

const StatusBadge = ({ status }: { status: string }) => {
  let color = "gray";
  if (status === "planifie") color = "blue";
  if (status === "en_cours") color = "orange";
  if (status === "termine") color = "green";
  return (
    <Badge colorPalette={color} variant="solid">
      {status}
    </Badge>
  );
};

export default TripManagementPage;
