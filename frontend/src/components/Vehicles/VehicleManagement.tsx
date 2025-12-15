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
  VStack,
} from "@chakra-ui/react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { useForm } from "react-hook-form"
import {
  FiAlertCircle,
  FiCheckCircle,
  FiEdit2,
  FiPlus,
  FiSearch,
  FiTrash2,
  FiTruck,
} from "react-icons/fi"

import {
  type ApiError,
  type VehicleCreate,
  type VehiclePublic,
  type VehicleUpdate,
  VehiclesService,
} from "@/client"
import {
  DialogActionTrigger,
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "@/components/ui/dialog"
import { Field } from "@/components/ui/field"
import { InputGroup } from "@/components/ui/input-group"
import {
  MenuContent,
  MenuItem,
  MenuRoot,
  MenuTrigger,
} from "@/components/ui/menu"
import { SkeletonText } from "@/components/ui/skeleton"
import { Toaster, toaster } from "@/components/ui/toaster"
import { handleError } from "@/utils"
import { useCompany } from "@/hooks/useCompany" // <--- 1. Import Hook

// --- Configuration & Helpers ---
const vehicleCategories = {
  ag1_camion_frigorifique: "Camion Frigorifique",
  ag2_camion_refrigere: "Camion Réfrigéré",
  bt1_camion_benne: "Camion-Benne",
  bt3_camion_malaxeur: "Camion Malaxeur",
  in1_camion_bache: "Camion Bâché",
  in3_camion_grue: "Camion-Grue",
  ch1_camion_citerne: "Camion-Citerne",
} as const

const statusConfig = {
  disponible: { label: "Disponible", color: "green", icon: FiCheckCircle },
  en_mission: { label: "En Mission", color: "blue", icon: FiTruck },
  maintenance: { label: "Maintenance", color: "orange", icon: FiAlertCircle },
  inactif: { label: "Inactif", color: "red", icon: FiAlertCircle },
}

const VehicleManagementPage = () => {
  const queryClient = useQueryClient()
  const { company } = useCompany() // <--- 2. Get company
  const [searchTerm, setSearchTerm] = useState("")
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingVehicle, setEditingVehicle] = useState<VehiclePublic | null>(null)

  // --- API Hooks ---
  const { data, isLoading } = useQuery({
    queryKey: ["vehicles"],
    queryFn: () => VehiclesService.readVehicles({ limit: 100 }),
    enabled: !!company, // <--- 3. Prevent fetch if no company (Fixes 404)
  })

  const createMutation = useMutation({
    mutationFn: (data: VehicleCreate) =>
      VehiclesService.createVehicle({ requestBody: data }),
    onSuccess: () => {
      toaster.success({ title: "Véhicule ajouté avec succès" })
      closeModal()
    },
    onError: (err: ApiError) => handleError(err),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["vehicles"] }),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: VehicleUpdate }) =>
      VehiclesService.updateVehicle({ vehicleId: id, requestBody: data }),
    onSuccess: () => {
      toaster.success({ title: "Véhicule mis à jour" })
      closeModal()
    },
    onError: (err: ApiError) => handleError(err),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["vehicles"] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => VehiclesService.deleteVehicle({ vehicleId: id }),
    onSuccess: () => toaster.success({ title: "Véhicule supprimé" }),
    onError: (err: ApiError) => handleError(err),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["vehicles"] }),
  })

  // --- Form Handling ---
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<VehicleCreate>()

  const openModal = (vehicle?: VehiclePublic) => {
    if (vehicle) {
      setEditingVehicle(vehicle)
      reset({
        ...vehicle,
        year: vehicle.year || new Date().getFullYear(),
      } as any)
    } else {
      setEditingVehicle(null)
      reset({
        status: "disponible",
        category: "ag1_camion_frigorifique",
        year: new Date().getFullYear(),
      })
    }
    setIsModalOpen(true)
  }

  const closeModal = () => {
    setIsModalOpen(false)
    setEditingVehicle(null)
    reset()
  }

  const onSubmit = (data: VehicleCreate) => {
    if (editingVehicle) {
      updateMutation.mutate({ id: editingVehicle.id, data: data as VehicleUpdate })
    } else {
      createMutation.mutate(data)
    }
  }

  // --- Statistics ---
  const vehicles = data?.data || []
  const filteredVehicles = vehicles.filter((v) =>
    v.license_plate.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  const stats = {
    total: vehicles.length,
    available: vehicles.filter((v) => v.status === "disponible").length,
    in_mission: vehicles.filter((v) => v.status === "en_mission").length,
    maintenance: vehicles.filter((v) => v.status === "maintenance").length,
  }

  return (
    <Container maxW="full" py={8} px={{ base: 4, md: 8 }}>
      <Toaster />
      
      {/* Header */}
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
            letterSpacing="tight"
          >
            Flotte de Véhicules
          </Heading>
          <Text color="gray.500" fontSize="lg">
            Gérez et suivez l'état de vos camions en temps réel.
          </Text>
        </Box>
        <Button
          colorPalette="brand"
          size="lg"
          onClick={() => openModal()}
          boxShadow="md"
        >
          <FiPlus /> Ajouter un Véhicule
        </Button>
      </Flex>

      {/* Stats Cards */}
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} gap={6} mb={8}>
        <StatCard label="Total Flotte" value={stats.total} color="brand.600" />
        <StatCard label="Disponibles" value={stats.available} color="green.600" />
        <StatCard label="En Mission" value={stats.in_mission} color="blue.600" />
        <StatCard label="Maintenance" value={stats.maintenance} color="orange.600" />
      </SimpleGrid>

      {/* Search & Table */}
      <CardRoot variant="elevated" borderRadius="xl" overflow="hidden" boxShadow="sm">
        <CardBody p={6}>
          <Flex mb={6} justify="space-between" wrap="wrap" gap={4}>
            <InputGroup
              flex="1"
              maxW="md"
              startElement={<FiSearch color="gray.400" />}
            >
              <Input
                placeholder="Rechercher par matricule..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                borderRadius="lg"
              />
            </InputGroup>
          </Flex>

          <Box overflowX="auto">
            <Table.Root interactive size="lg">
              <Table.Header bg="gray.50">
                <Table.Row>
                  <Table.ColumnHeader>Matricule</Table.ColumnHeader>
                  <Table.ColumnHeader>Détails</Table.ColumnHeader>
                  <Table.ColumnHeader>Capacité</Table.ColumnHeader>
                  <Table.ColumnHeader>Statut</Table.ColumnHeader>
                  <Table.ColumnHeader textAlign="right">Actions</Table.ColumnHeader>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {isLoading ? (
                  [...Array(3)].map((_, i) => (
                    <Table.Row key={i}>
                      <Table.Cell colSpan={5}>
                        <SkeletonText noOfLines={1} />
                      </Table.Cell>
                    </Table.Row>
                  ))
                ) : filteredVehicles.length === 0 ? (
                  <Table.Row>
                    <Table.Cell colSpan={5} textAlign="center" py={8} color="gray.500">
                      {company ? "Aucun véhicule trouvé." : "Veuillez d'abord configurer votre entreprise."}
                    </Table.Cell>
                  </Table.Row>
                ) : (
                  filteredVehicles.map((vehicle) => {
                    const status = statusConfig[vehicle.status as keyof typeof statusConfig]
                    return (
                      <Table.Row key={vehicle.id} transition="background 0.2s">
                        <Table.Cell fontWeight="bold" color="brand.700">
                          {vehicle.license_plate}
                        </Table.Cell>
                        <Table.Cell>
                          <VStack align="start" gap={0}>
                            <Text fontWeight="medium">
                              {vehicleCategories[vehicle.category as keyof typeof vehicleCategories]}
                            </Text>
                            <Text fontSize="xs" color="gray.500">
                              {vehicle.brand} {vehicle.model} ({vehicle.year})
                            </Text>
                          </VStack>
                        </Table.Cell>
                        <Table.Cell>{vehicle.capacity_tons} T</Table.Cell>
                        <Table.Cell>
                          <Badge
                            colorPalette={status.color}
                            variant="subtle"
                            px={2}
                            py={1}
                            borderRadius="full"
                          >
                            <Flex align="center" gap={1}>
                              <Icon as={status.icon} /> {status.label}
                            </Flex>
                          </Badge>
                        </Table.Cell>
                        <Table.Cell textAlign="right">
                          <MenuRoot>
                            <MenuTrigger asChild>
                              <IconButton variant="ghost" size="sm" aria-label="Actions">
                                <Box as="span">•••</Box>
                              </IconButton>
                            </MenuTrigger>
                            <MenuContent>
                              <MenuItem onClick={() => openModal(vehicle)} value="edit">
                                <FiEdit2 /> Modifier
                              </MenuItem>
                              <MenuItem
                                onClick={() => {
                                  if (confirm("Supprimer ce véhicule ?"))
                                    deleteMutation.mutate(vehicle.id)
                                }}
                                color="red.500"
                                value="delete"
                              >
                                <FiTrash2 /> Supprimer
                              </MenuItem>
                            </MenuContent>
                          </MenuRoot>
                        </Table.Cell>
                      </Table.Row>
                    )
                  })
                )}
              </Table.Body>
            </Table.Root>
          </Box>
        </CardBody>
      </CardRoot>

      {/* Add/Edit Modal */}
      <DialogRoot open={isModalOpen} onOpenChange={(e) => !e.open && closeModal()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingVehicle ? "Modifier le Véhicule" : "Nouveau Véhicule"}
            </DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Stack gap={4} as="form" id="vehicle-form" onSubmit={handleSubmit(onSubmit)}>
              <Field
                label="Matricule"
                invalid={!!errors.license_plate}
                errorText={errors.license_plate?.message}
                required
              >
                <Input
                  {...register("license_plate", { required: "Requis" })}
                  placeholder="ex: 12345-116-16"
                />
              </Field>

              <SimpleGrid columns={2} gap={4}>
                <Field label="Marque" invalid={!!errors.brand}>
                  <Input {...register("brand")} placeholder="Renault" />
                </Field>
                <Field label="Modèle" invalid={!!errors.model}>
                  <Input {...register("model")} placeholder="K-Series" />
                </Field>
              </SimpleGrid>

              <SimpleGrid columns={2} gap={4}>
                <Field label="Capacité (T)" invalid={!!errors.capacity_tons} required>
                  <Input
                    type="number"
                    step="0.1"
                    {...register("capacity_tons", { required: "Requis" })}
                  />
                </Field>
                <Field label="Année" invalid={!!errors.year}>
                  <Input type="number" {...register("year")} />
                </Field>
              </SimpleGrid>

              <Field label="Catégorie" required>
                <select
                  {...register("category")}
                  style={{
                    width: "100%",
                    padding: "8px",
                    borderRadius: "6px",
                    border: "1px solid #E2E8F0",
                  }}
                >
                  {Object.entries(vehicleCategories).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v}
                    </option>
                  ))}
                </select>
              </Field>

              <Field label="Statut" required>
                <select
                  {...register("status")}
                  style={{
                    width: "100%",
                    padding: "8px",
                    borderRadius: "6px",
                    border: "1px solid #E2E8F0",
                  }}
                >
                  {Object.keys(statusConfig).map((s) => (
                    <option key={s} value={s}>
                      {statusConfig[s as keyof typeof statusConfig].label}
                    </option>
                  ))}
                </select>
              </Field>
            </Stack>
          </DialogBody>
          <DialogFooter>
            <DialogActionTrigger asChild>
              <Button variant="ghost" onClick={closeModal}>
                Annuler
              </Button>
            </DialogActionTrigger>
            <Button
              form="vehicle-form"
              type="submit"
              loading={isSubmitting || createMutation.isPending || updateMutation.isPending}
              colorPalette="brand"
            >
              Enregistrer
            </Button>
          </DialogFooter>
          <DialogCloseTrigger />
        </DialogContent>
      </DialogRoot>
    </Container>
  )
}

const StatCard = ({ label, value, color }: { label: string; value: number; color: string }) => (
  <CardRoot borderRadius="xl" borderTop="4px solid" borderColor={color} boxShadow="sm">
    <CardBody>
      <Text fontSize="sm" color="gray.500" fontWeight="medium">
        {label}
      </Text>
      <Text fontSize="3xl" fontWeight="bold" color={color}>
        {value}
      </Text>
    </CardBody>
  </CardRoot>
)

export default VehicleManagementPage