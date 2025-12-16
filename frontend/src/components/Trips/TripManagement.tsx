import {
  Badge,
  Box,
  Button,
  CardBody,
  CardRoot,
  Container,
  Flex,
  Heading,
  HStack,
  Icon,
  IconButton,
  Input,
  SimpleGrid,
  Stack,
  Table,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import {
  FiCalendar,
  FiCheckCircle,
  FiClock,
  FiUpload,
  FiMap,
  FiList,
  FiZap,
  FiPlus,
  FiSearch,
  FiMapPin,
  FiX,
} from "react-icons/fi";

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
import { Field } from "@/components/ui/field";
import { InputGroup } from "@/components/ui/input-group";
import { SkeletonText } from "@/components/ui/skeleton";
import { Toaster, toaster } from "@/components/ui/toaster";
import TripMap, { type DraftPoint } from "./TripMap";
import { handleError } from "@/utils";
import { useCompany } from "@/hooks/useCompany";
import { GeocodingService } from "@/utils";

// ... (Keep existing CARGO_CATEGORIES and VEHICLE_CATEGORIES constants) ...
const CARGO_CATEGORIES = [
  { value: "a01_produits_frais", label: "A01 - Produits Frais" },
  { value: "a02_produits_surgeles", label: "A02 - Produits Surgelés" },
  { value: "a03_produits_secs", label: "A03 - Produits Secs" },
  { value: "a04_boissons_liquides", label: "A04 - Boissons Liquides" },
  { value: "a05_produits_agricoles_bruts", label: "A05 - Agricoles Bruts" },
  { value: "b01_materiaux_vrac", label: "B01 - Matériaux Vrac" },
  { value: "b02_materiaux_solides", label: "B02 - Matériaux Solides" },
  { value: "b03_beton_pret", label: "B03 - Béton Prêt" },
  { value: "c01_chimiques_liquides", label: "C01 - Chimiques Liquides" },
  { value: "c04_hydrocarbures", label: "C04 - Hydrocarbures" },
  { value: "i01_produits_finis", label: "I01 - Produits Finis" },
  { value: "i04_emballages_palettes", label: "I04 - Emballages/Palettes" },
];

const VEHICLE_CATEGORIES = [
  { value: "", label: "-- Automatique (Selon Cargo) --" },
  { value: "ag1_camion_frigorifique", label: "AG1 - Frigorifique" },
  { value: "bt1_camion_benne", label: "BT1 - Benne" },
  { value: "in1_camion_bache", label: "IN1 - Bâché" },
  { value: "ch1_camion_citerne_hydrocarbures", label: "CH1 - Citerne Hydro" },
];

interface TripFormValues {
  departure_name: string;
  departure_lat: number;
  departure_lng: number;
  arrival_name: string;
  arrival_lat: number;
  arrival_lng: number;
  departure_time: string;
  cargo_category: string;
  cargo_weight_kg: number;
  cargo_volume_m3?: number;
  required_vehicle_category?: string;
  vehicle_id?: string;
}

const getToday = () => new Date().toISOString().split("T")[0];

const TripManagementPage = () => {
  const queryClient = useQueryClient();
  const { company } = useCompany();
  const [selectedDate, setSelectedDate] = useState(getToday());
  const [viewMode, setViewMode] = useState<"list" | "map">("list");

  // States
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [pickingMode, setPickingMode] = useState<
    "departure" | "arrival" | null
  >(null);
  const [, setIsGeocoding] = useState(false);

  // Form
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    getValues,
    formState: {},
  } = useForm<TripFormValues>({
    defaultValues: {
      cargo_category: "a01_produits_frais",
      departure_time: `${getToday()}T08:00`,
    },
  });

  // Watchers
  const depLat = watch("departure_lat");
  const depLng = watch("departure_lng");
  const arrLat = watch("arrival_lat");
  const arrLng = watch("arrival_lng");

  const draftDeparture: DraftPoint | null = depLat
    ? { lat: depLat, lng: depLng, name: watch("departure_name") }
    : null;
  const draftArrival: DraftPoint | null = arrLat
    ? { lat: arrLat, lng: arrLng, name: watch("arrival_name") }
    : null;

  // Queries
  const shouldFetch = !!company;
  const { data: tripsData, isLoading: isLoadingList } = useQuery({
    queryKey: ["trips", selectedDate],
    queryFn: () => ExtendedTripsService.getTripsByDate(selectedDate),
    enabled: shouldFetch,
  });
  const { data: mapData } = useQuery({
    queryKey: ["tripsMap", selectedDate],
    queryFn: () => ExtendedTripsService.getMapData(selectedDate),
    enabled: shouldFetch && viewMode === "map",
  });
  const { data: kpiData } = useQuery({
    queryKey: ["tripsKPI", selectedDate],
    queryFn: () => ExtendedTripsService.getKPIs(selectedDate),
    enabled: shouldFetch,
  });

  // --- STRICT FORM SUBMISSION ---
  const createTripMutation = useMutation({
    mutationFn: (data: FormData) =>
      (ExtendedTripsService as any).createTripFromMap(data),
    onSuccess: () => {
      toaster.success({
        title: "Trajet créé",
        description: "Ajouté à la planification.",
      });
      setIsAddOpen(false);
      reset();
      setPickingMode(null);
      // Force refresh of map data to show the new trip
      queryClient.invalidateQueries({ queryKey: ["trips"] });
      queryClient.invalidateQueries({ queryKey: ["tripsMap"] });
    },
    onError: (err: any) => {
      // Log detailed error for debugging
      console.error("Submission error:", err);
      handleError(err);
    },
  });

  const onSubmit = (data: TripFormValues) => {
    if (!data.departure_lat || !data.arrival_lat) {
      toaster.error({
        title: "Erreur",
        description: "Veuillez définir le départ et l'arrivée.",
      });
      return;
    }

    const formData = new FormData();

    // 1. Required Fields
    formData.append("departure_lat", String(data.departure_lat));
    formData.append("departure_lng", String(data.departure_lng));
    formData.append("departure_name", data.departure_name || "Point A");

    formData.append("arrival_lat", String(data.arrival_lat));
    formData.append("arrival_lng", String(data.arrival_lng));
    formData.append("arrival_name", data.arrival_name || "Point B");

    // Ensure ISO-8601 with Timezone info if possible, or simple ISO
    const isoDate = new Date(data.departure_time).toISOString();
    formData.append("departure_time", isoDate);

    formData.append("cargo_category", data.cargo_category);
    formData.append("cargo_weight_kg", String(data.cargo_weight_kg));

    // 2. Optional Fields (Only append if they have values)
    if (data.cargo_volume_m3 && data.cargo_volume_m3 > 0) {
      formData.append("cargo_volume_m3", String(data.cargo_volume_m3));
    }

    // Check for empty string on select
    if (
      data.required_vehicle_category &&
      data.required_vehicle_category !== ""
    ) {
      formData.append(
        "required_vehicle_category",
        data.required_vehicle_category
      );
    }

    if (data.vehicle_id && data.vehicle_id.trim() !== "") {
      formData.append("vehicle_id", data.vehicle_id);
    }

    createTripMutation.mutate(formData);
  };

  // ... (Keep existing handlers for Map Click, Search, Upload, Optimize) ...
  const handleMapClick = async (lat: number, lng: number) => {
    if (!pickingMode) return;

    const loadId = toaster.create({ title: "Géocodage...", type: "loading" });
    setIsGeocoding(true);
    const address = await GeocodingService.reverseGeocode(lat, lng);

    const target = pickingMode;
    setValue(`${target}_lat`, lat);
    setValue(`${target}_lng`, lng);
    setValue(
      `${target}_name`,
      address || `Point ${lat.toFixed(4)}, ${lng.toFixed(4)}`
    );

    setIsGeocoding(false);
    toaster.dismiss(loadId);
    toaster.info({
      title: "Position définie",
      description: address || "Coordonnées GPS",
    });

    if (target === "departure" && !getValues("arrival_lat")) {
      setPickingMode("arrival");
      toaster.info({
        title: "Étape suivante",
        description: "Sélectionnez l'arrivée",
      });
    } else {
      setPickingMode(null);
      setIsAddOpen(true);
    }
  };

  const handleSearch = async (fieldPrefix: "departure" | "arrival") => {
    const query = getValues(`${fieldPrefix}_name`);
    if (!query) return;

    setIsGeocoding(true);
    const result = await GeocodingService.searchAddress(query);
    setIsGeocoding(false);

    if (result) {
      setValue(`${fieldPrefix}_lat`, result.lat);
      setValue(`${fieldPrefix}_lng`, result.lng);
      setValue(`${fieldPrefix}_name`, result.display_name);
      toaster.success({
        title: "Adresse trouvée",
        description: result.display_name,
      });
    } else {
      toaster.error({
        title: "Introuvable",
        description: "Adresse non trouvée.",
      });
    }
  };

  const startPicking = (mode: "departure" | "arrival") => {
    setViewMode("map");
    setIsAddOpen(false);
    setPickingMode(mode);
  };

  const cancelPicking = () => {
    setPickingMode(null);
    setIsAddOpen(true);
  };

  // ... (Other mutation handlers: uploadMutation, optimizeMutation same as before) ...
  const uploadMutation = useMutation({
    mutationFn: (formData: FormData) =>
      ExtendedTripsService.uploadTrips(formData),
    onSuccess: (res: UploadResponse) => {
      toaster.success({
        title: "Import réussi",
        description: `${res.summary.successful} trajets.`,
      });
      setIsUploadOpen(false);
      setFile(null);
      queryClient.invalidateQueries({ queryKey: ["trips"] });
    },
    onError: (err: any) => handleError(err),
  });

  const optimizeMutation = useMutation({
    mutationFn: () => ExtendedTripsService.optimize(selectedDate),
    onSuccess: (res: OptimizationResponse) => {
      toaster.success({
        title: "Optimisation lancée",
        description: `Batch ID: ${res.details.trips_optimized}`,
      });
      setTimeout(
        () => queryClient.invalidateQueries({ queryKey: ["trips"] }),
        2000
      );
    },
    onError: (err: any) => handleError(err),
  });

  const handleUploadSubmit = () => {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    formData.append("file_type", file.name.endsWith(".xlsx") ? "excel" : "csv");
    uploadMutation.mutate(formData);
  };

  const summary = kpiData?.summary || { trips_contributed: 0 };
  const savings = kpiData?.savings || { km_saved: 0, fuel_saved_liters: 0 };

  return (
    <Container maxW="full" py={8} px={{ base: 4, md: 8 }}>
      <Toaster />

      {/* Header */}
      <Flex justify="space-between" mb={8} wrap="wrap" gap={4}>
        <Box>
          <Heading size="2xl" mb={2} color="fg.default">
            Planification
          </Heading>
          <Text color="fg.muted">
            Gérez vos trajets et optimisez les tournées.
          </Text>
        </Box>
        <Stack direction="row" gap={3}>
          <Input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            w="auto"
            bg="bg.panel"
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
              onClick={() => setViewMode("list")}
            >
              <FiList />
            </IconButton>
            <IconButton
              variant={viewMode === "map" ? "solid" : "ghost"}
              onClick={() => setViewMode("map")}
            >
              <FiMap />
            </IconButton>
          </HStack>
          <Button colorPalette="brand" onClick={() => setIsAddOpen(true)}>
            <FiPlus /> Nouveau Trajet
          </Button>
          <Button
            colorPalette="orange"
            variant="surface"
            onClick={() => optimizeMutation.mutate()}
          >
            <FiZap /> Optimiser
          </Button>
          <Button variant="outline" onClick={() => setIsUploadOpen(true)}>
            <FiUpload /> CSV
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

      {/* Content */}
      <CardRoot
        variant="elevated"
        borderRadius="xl"
        bg="bg.panel"
        boxShadow="sm"
      >
        <CardBody p={viewMode === "map" ? 0 : 6}>
          {viewMode === "map" ? (
            <Box position="relative" h="600px" w="full">
              {/* The Map */}
              <TripMap
                data={mapData}
                draftDeparture={draftDeparture}
                draftArrival={draftArrival}
                onMapClick={handleMapClick}
              />

              {/* Picking Mode Banner */}
              {pickingMode && (
                <Box
                  position="absolute"
                  top={4}
                  left="50%"
                  transform="translateX(-50%)"
                  zIndex={1000}
                >
                  <VStack>
                    <Badge
                      size="lg"
                      colorPalette={
                        pickingMode === "departure" ? "blue" : "red"
                      }
                      variant="solid"
                      px={4}
                      py={2}
                      boxShadow="lg"
                    >
                      <HStack>
                        <FiMapPin />
                        <Text fontWeight="bold" fontSize="md">
                          Cliquez sur la carte :{" "}
                          {pickingMode === "departure" ? "DÉPART" : "ARRIVÉE"}
                        </Text>
                      </HStack>
                    </Badge>
                    <Button
                      size="xs"
                      variant="surface"
                      bg="white"
                      onClick={cancelPicking}
                      boxShadow="md"
                    >
                      <FiX /> Annuler / Retour au formulaire
                    </Button>
                  </VStack>
                </Box>
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
                  ) : (
                    tripsData?.data?.map((trip: any) => (
                      <Table.Row key={trip.id}>
                        <Table.Cell fontWeight="medium">
                          {trip.departure_point}
                        </Table.Cell>
                        <Table.Cell>{trip.arrival_point}</Table.Cell>
                        <Table.Cell color="fg.muted">
                          {new Date(trip.departure_datetime).toLocaleString()}
                        </Table.Cell>
                        <Table.Cell>{trip.cargo_category}</Table.Cell>
                        <Table.Cell>
                          <StatusBadge status={trip.status} />
                        </Table.Cell>
                      </Table.Row>
                    ))
                  )}
                </Table.Body>
              </Table.Root>
            </Box>
          )}
        </CardBody>
      </CardRoot>

      {/* --- ADD TRIP MODAL --- */}
      <DialogRoot
        open={isAddOpen}
        onOpenChange={(e) => setIsAddOpen(e.open)}
        size="lg"
        unmountOnExit={false}
      >
        {!pickingMode && (
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Créer un Trajet</DialogTitle>
            </DialogHeader>
            <DialogBody>
              <form id="create-trip-form" onSubmit={handleSubmit(onSubmit)}>
                <Stack gap={5}>
                  {/* DEPARTURE */}
                  <Box
                    p={4}
                    borderWidth="1px"
                    borderRadius="md"
                    borderColor="blue.200"
                    bg="blue.50/20"
                  >
                    <Text fontWeight="bold" mb={2} color="blue.600">
                      Point de Départ
                    </Text>
                    <InputGroup
                      w="full"
                      endElement={
                        <IconButton
                          size="sm"
                          variant="ghost"
                          onClick={() => handleSearch("departure")}
                        >
                          <FiSearch />
                        </IconButton>
                      }
                    >
                      <Input
                        {...register("departure_name", { required: true })}
                        placeholder="Rechercher une adresse..."
                      />
                    </InputGroup>
                    <HStack mt={2} justify="space-between">
                      <Text fontSize="xs" color="fg.muted">
                        {watch("departure_lat") ? "Localisé ✅" : "Non défini"}
                      </Text>
                      <Button
                        size="xs"
                        variant="outline"
                        colorPalette="blue"
                        onClick={() => startPicking("departure")}
                      >
                        <FiMapPin /> Carte
                      </Button>
                    </HStack>
                    <input type="hidden" {...register("departure_lat")} />
                    <input type="hidden" {...register("departure_lng")} />
                  </Box>

                  {/* ARRIVAL */}
                  <Box
                    p={4}
                    borderWidth="1px"
                    borderRadius="md"
                    borderColor="red.200"
                    bg="red.50/20"
                  >
                    <Text fontWeight="bold" mb={2} color="red.600">
                      Point d'Arrivée
                    </Text>
                    <InputGroup
                      w="full"
                      endElement={
                        <IconButton
                          size="sm"
                          variant="ghost"
                          onClick={() => handleSearch("arrival")}
                        >
                          <FiSearch />
                        </IconButton>
                      }
                    >
                      <Input
                        {...register("arrival_name", { required: true })}
                        placeholder="Rechercher une adresse..."
                      />
                    </InputGroup>
                    <HStack mt={2} justify="space-between">
                      <Text fontSize="xs" color="fg.muted">
                        {watch("arrival_lat") ? "Localisé ✅" : "Non défini"}
                      </Text>
                      <Button
                        size="xs"
                        variant="outline"
                        colorPalette="red"
                        onClick={() => startPicking("arrival")}
                      >
                        <FiMapPin /> Carte
                      </Button>
                    </HStack>
                    <input type="hidden" {...register("arrival_lat")} />
                    <input type="hidden" {...register("arrival_lng")} />
                  </Box>

                  <SimpleGrid columns={2} gap={4}>
                    <Field label="Date de départ" required>
                      <Input
                        type="datetime-local"
                        {...register("departure_time", { required: true })}
                      />
                    </Field>
                    <Field label="Poids (kg)" required>
                      <Input
                        type="number"
                        {...register("cargo_weight_kg", {
                          required: true,
                          valueAsNumber: true,
                        })}
                        placeholder="12500"
                      />
                    </Field>
                  </SimpleGrid>

                  <SimpleGrid columns={2} gap={4}>
                    <Field label="Volume (m3) - Optionnel">
                      <Input
                        type="number"
                        {...register("cargo_volume_m3", {
                          valueAsNumber: true,
                        })}
                        placeholder="20"
                      />
                    </Field>
                    <Field label="Véhicule Assigné (Optionnel)">
                      <Input {...register("vehicle_id")} placeholder="UUID" />
                    </Field>
                  </SimpleGrid>

                  <Field label="Catégorie de Cargaison" required>
                    <select
                      {...register("cargo_category", { required: true })}
                      style={{
                        width: "100%",
                        padding: "10px",
                        borderRadius: "6px",
                        border: "1px solid #E2E8F0",
                        background: "transparent",
                      }}
                    >
                      {CARGO_CATEGORIES.map((c) => (
                        <option key={c.value} value={c.value}>
                          {c.label}
                        </option>
                      ))}
                    </select>
                  </Field>

                  <Field label="Catégorie Véhicule Requise (Optionnel)">
                    <select
                      {...register("required_vehicle_category")}
                      style={{
                        width: "100%",
                        padding: "10px",
                        borderRadius: "6px",
                        border: "1px solid #E2E8F0",
                        background: "transparent",
                      }}
                    >
                      {VEHICLE_CATEGORIES.map((c) => (
                        <option key={c.value} value={c.value}>
                          {c.label}
                        </option>
                      ))}
                    </select>
                  </Field>
                </Stack>
              </form>
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
                Confirmer le Trajet
              </Button>
            </DialogFooter>
            <DialogCloseTrigger />
          </DialogContent>
        )}
      </DialogRoot>

      {/* Upload Modal (Keep existing) */}
      <DialogRoot
        open={isUploadOpen}
        onOpenChange={(e) => setIsUploadOpen(e.open)}
      >
        {/* ... content same as before ... */}
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Importer CSV</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Input
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </DialogBody>
          <DialogFooter>
            <Button onClick={handleUploadSubmit}>Uploader</Button>
          </DialogFooter>
        </DialogContent>
      </DialogRoot>
    </Container>
  );
};

// ... (StatCard and StatusBadge helpers remain same) ...
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
