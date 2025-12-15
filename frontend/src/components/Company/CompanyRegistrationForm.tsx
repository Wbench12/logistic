import {
  Badge,
  Box,
  Button,
  CardBody,
  CardRoot,
  Container,
  Flex,
  Heading,
  Icon,
  IconButton,
  Input,
  SimpleGrid,
  Stack,
  Table,
  Text,
} from "@chakra-ui/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import {
  FiCalendar,
  FiCheckCircle,
  FiClock,
  FiEdit2,
  FiMoreVertical,
  FiPlus,
  FiTrash2,
  FiZap,
} from "react-icons/fi";

import {
  type ApiError,
  type TripCreate,
  type TripPublic,
  type TripUpdate,
  TripsService,
} from "@/client";
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
import {
  MenuContent,
  MenuItem,
  MenuRoot,
  MenuTrigger,
} from "@/components/ui/menu";
import { SkeletonText } from "@/components/ui/skeleton";
import { Toaster, toaster } from "@/components/ui/toaster";
import { handleError } from "@/utils";

// --- Configuration ---
const statusConfig = {
  planifie: { label: "Planifié", color: "purple" },
  en_cours: { label: "En Cours", color: "blue" },
  termine: { label: "Terminé", color: "green" },
  annule: { label: "Annulé", color: "red" },
};

const cargoCategories = {
  a01_produits_frais: "Produits Frais",
  b01_materiaux_vrac: "Matériaux Vrac",
  i01_produits_finis: "Produits Finis",
  // Add other categories as needed based on API types
};

const TripManagementPage = () => {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTrip, setEditingTrip] = useState<TripPublic | null>(null);

  // --- API ---
  const { data, isLoading } = useQuery({
    queryKey: ["trips"],
    queryFn: () => TripsService.readTrips({ limit: 100 }),
  });

  // Optimize Mutation
  const optimizeMutation = useMutation({
    mutationFn: () =>
      TripsService.optimizeTrips({
        date: new Date().toISOString().split("T")[0],
      }),
    onSuccess: () => {
      toaster.success({
        title: "Optimisation lancée",
        description: "L'algorithme calcule les meilleurs itinéraires...",
      });
    },
    onError: (err: ApiError) => handleError(err),
  });

  const createMutation = useMutation({
    mutationFn: (data: TripCreate) =>
      TripsService.createTrip({ requestBody: data }),
    onSuccess: () => {
      toaster.success({ title: "Trajet créé" });
      closeModal();
    },
    onError: (err: ApiError) => handleError(err),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["trips"] }),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: TripUpdate }) =>
      TripsService.updateTrip({ tripId: id, requestBody: data }),
    onSuccess: () => {
      toaster.success({ title: "Trajet mis à jour" });
      closeModal();
    },
    onError: (err: ApiError) => handleError(err),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["trips"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => TripsService.deleteTrip({ tripId: id }),
    onSuccess: () => toaster.success({ title: "Trajet supprimé" }),
    onError: (err: ApiError) => handleError(err),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["trips"] }),
  });

  // --- Form ---
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<TripCreate>();

  const openModal = (trip?: TripPublic) => {
    if (trip) {
      setEditingTrip(trip);
      reset(trip as any); // Type casting for ease, in real app map fields properly
    } else {
      setEditingTrip(null);
      reset({
        status: "planifie",
        cargo_category: "a01_produits_frais",
        material_type: "solide",
      });
    }
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingTrip(null);
    reset();
  };

  const onSubmit = (data: TripCreate) => {
    const payload: any = {
      ...data,
      cargo_weight_kg: Number((data as any).cargo_weight_kg),
    };
    if (!payload.vehicle_id) {
      payload.vehicle_id = null;
    }

    if (editingTrip) {
      updateMutation.mutate({
        id: editingTrip.id,
        data: payload as TripUpdate,
      });
    } else {
      createMutation.mutate(payload);
    }
  };

  const trips = data?.data || [];
  const stats = {
    total: trips.length,
    planned: trips.filter((t) => t.status === "planifie").length,
    active: trips.filter((t) => t.status === "en_cours").length,
  };

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
          <Heading
            size="2xl"
            mb={2}
            bgGradient="linear(to-r, brand.700, brand.500)"
            bgClip="text"
          >
            Gestion des Trajets
          </Heading>
          <Text color="gray.500" fontSize="lg">
            Planification et optimisation logistique.
          </Text>
        </Box>
        <Stack direction="row" gap={3}>
          <Button
            colorPalette="orange"
            variant="surface"
            size="lg"
            onClick={() => optimizeMutation.mutate()}
            loading={optimizeMutation.isPending}
          >
            <FiZap /> Optimiser (IA)
          </Button>
          <Button
            colorPalette="brand"
            size="lg"
            onClick={() => openModal()}
            boxShadow="md"
          >
            <FiPlus /> Nouveau Trajet
          </Button>
        </Stack>
      </Flex>

      <SimpleGrid columns={{ base: 1, md: 3 }} gap={6} mb={8}>
        <StatCard
          label="Total Trajets"
          value={stats.total}
          color="brand.600"
          icon={FiCalendar}
        />
        <StatCard
          label="Planifiés"
          value={stats.planned}
          color="purple.600"
          icon={FiClock}
        />
        <StatCard
          label="En Cours"
          value={stats.active}
          color="blue.600"
          icon={FiCheckCircle}
        />
      </SimpleGrid>

      <CardRoot variant="elevated" borderRadius="xl" boxShadow="sm">
        <CardBody p={0}>
          <Box overflowX="auto">
            <Table.Root interactive size="lg">
              <Table.Header bg="gray.50">
                <Table.Row>
                  <Table.ColumnHeader>Trajet</Table.ColumnHeader>
                  <Table.ColumnHeader>Véhicule</Table.ColumnHeader>
                  <Table.ColumnHeader>Horaires</Table.ColumnHeader>
                  <Table.ColumnHeader>Cargaison</Table.ColumnHeader>
                  <Table.ColumnHeader>Statut</Table.ColumnHeader>
                  <Table.ColumnHeader textAlign="right">
                    Actions
                  </Table.ColumnHeader>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {isLoading ? (
                  <Table.Row>
                    <Table.Cell colSpan={6}>
                      <SkeletonText noOfLines={3} gap={4} />
                    </Table.Cell>
                  </Table.Row>
                ) : (
                  trips.map((trip) => {
                    const status =
                      statusConfig[trip.status as keyof typeof statusConfig] ||
                      statusConfig.planifie;
                    return (
                      <Table.Row key={trip.id}>
                        <Table.Cell>
                          <Text fontWeight="bold">{trip.departure_point}</Text>
                          <Text fontSize="sm" color="gray.500">
                            ↓ {trip.arrival_point}
                          </Text>
                        </Table.Cell>
                        <Table.Cell>
                          <Badge variant="surface">{trip.vehicle_id}</Badge>
                          <Text fontSize="xs" color="gray.500" mt={1}>
                            {trip.driver_name || "Sans chauffeur"}
                          </Text>
                        </Table.Cell>
                        <Table.Cell>
                          <Text fontSize="sm">
                            {new Date(
                              trip.departure_datetime
                            ).toLocaleDateString()}
                          </Text>
                          <Text fontSize="xs" color="gray.500">
                            {new Date(
                              trip.departure_datetime
                            ).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </Text>
                        </Table.Cell>
                        <Table.Cell>
                          <Text fontSize="sm">
                            {cargoCategories[
                              trip.cargo_category as keyof typeof cargoCategories
                            ] || trip.cargo_category}
                          </Text>
                          <Text fontSize="xs">{trip.cargo_weight_kg} kg</Text>
                        </Table.Cell>
                        <Table.Cell>
                          <Badge
                            colorPalette={status.color}
                            borderRadius="full"
                            px={2}
                          >
                            {status.label}
                          </Badge>
                        </Table.Cell>
                        <Table.Cell textAlign="right">
                          <MenuRoot>
                            <MenuTrigger asChild>
                              <IconButton
                                variant="ghost"
                                size="sm"
                                aria-label="options"
                              >
                                <FiMoreVertical />
                              </IconButton>
                            </MenuTrigger>
                            <MenuContent>
                              <MenuItem
                                onClick={() => openModal(trip)}
                                value="edit"
                              >
                                <FiEdit2 /> Modifier
                              </MenuItem>
                              <MenuItem
                                onClick={() => deleteMutation.mutate(trip.id)}
                                color="red.500"
                                value="delete"
                              >
                                <FiTrash2 /> Supprimer
                              </MenuItem>
                            </MenuContent>
                          </MenuRoot>
                        </Table.Cell>
                      </Table.Row>
                    );
                  })
                )}
              </Table.Body>
            </Table.Root>
          </Box>
        </CardBody>
      </CardRoot>

      {/* Modal */}
      <DialogRoot
        open={isModalOpen}
        onOpenChange={(e) => !e.open && closeModal()}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingTrip ? "Modifier" : "Nouveau"} Trajet
            </DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Stack
              gap={4}
              as="form"
              id="trip-form"
              onSubmit={handleSubmit(onSubmit)}
            >
              <SimpleGrid columns={2} gap={4}>
                <Field
                  label="Départ"
                  invalid={!!errors.departure_point}
                  required
                >
                  <Input
                    {...register("departure_point", { required: "Requis" })}
                  />
                </Field>
                <Field
                  label="Arrivée"
                  invalid={!!errors.arrival_point}
                  required
                >
                  <Input
                    {...register("arrival_point", { required: "Requis" })}
                  />
                </Field>
              </SimpleGrid>

              <SimpleGrid columns={2} gap={4}>
                <Field
                  label="Date/Heure Départ"
                  invalid={!!errors.departure_datetime}
                  required
                >
                  <Input
                    type="datetime-local"
                    {...register("departure_datetime", { required: "Requis" })}
                  />
                </Field>
                <Field label="Date/Heure Arrivée (Estimée)" required>
                  <Input
                    type="datetime-local"
                    {...register("arrival_datetime_planned", {
                      required: "Requis",
                    })}
                  />
                </Field>
              </SimpleGrid>

              <SimpleGrid columns={2} gap={4}>
                <Field label="Véhicule ID" required>
                  <Input {...register("vehicle_id", { required: "Requis" })} />
                </Field>
                <Field label="Chauffeur">
                  <Input {...register("driver_name")} />
                </Field>
              </SimpleGrid>

              <SimpleGrid columns={2} gap={4}>
                <Field label="Poids (kg)" required>
                  <Input
                    type="number"
                    {...register("cargo_weight_kg", { required: "Requis" })}
                  />
                </Field>
                <Field label="Type" required>
                  <select
                    {...register("material_type")}
                    style={{
                      width: "100%",
                      padding: "8px",
                      borderRadius: "6px",
                      border: "1px solid #E2E8F0",
                    }}
                  >
                    <option value="solide">Solide</option>
                    <option value="liquide">Liquide</option>
                    <option value="gaz">Gaz</option>
                  </select>
                </Field>
              </SimpleGrid>
            </Stack>
          </DialogBody>
          <DialogFooter>
            <DialogActionTrigger asChild>
              <Button variant="ghost" onClick={closeModal}>
                Annuler
              </Button>
            </DialogActionTrigger>
            <Button
              form="trip-form"
              type="submit"
              loading={isSubmitting || createMutation.isPending}
              colorPalette="brand"
            >
              Enregistrer
            </Button>
          </DialogFooter>
          <DialogCloseTrigger />
        </DialogContent>
      </DialogRoot>
    </Container>
  );
};

const StatCard = ({
  label,
  value,
  color,
  icon: IconComp,
}: {
  label: string;
  value: number;
  color: string;
  icon: any;
}) => (
  <CardRoot
    borderRadius="xl"
    borderLeft="4px solid"
    borderColor={color}
    boxShadow="sm"
  >
    <CardBody>
      <Flex justify="space-between" align="center">
        <Box>
          <Text fontSize="sm" color="gray.500" fontWeight="medium">
            {label}
          </Text>
          <Text fontSize="3xl" fontWeight="bold" color={color}>
            {value}
          </Text>
        </Box>
        <Box p={2} bg={`${color.split(".")[0]}.50`} borderRadius="lg">
          <Icon as={IconComp} size="lg" color={color} />
        </Box>
      </Flex>
    </CardBody>
  </CardRoot>
);

export default TripManagementPage;
