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
  DialogTitle,
  Flex,
  Heading,
  IconButton,
  Input,
  InputGroup,
  MenuContent,
  MenuItem,
  MenuRoot,
  MenuTrigger,
  SimpleGrid,
  Stack,
  type StackProps,
  TableBody,
  TableCell,
  TableColumnHeader,
  TableHeader,
  TableRoot,
  TableRow,
  Text,
  useDisclosure,
} from "@chakra-ui/react";
import {
  type ChangeEvent,
  type ComponentType,
  type ReactNode,
  useMemo,
  useState,
} from "react";
import {
  FiAlertCircle,
  FiCheckCircle,
  FiEdit2,
  FiMoreVertical,
  FiPlus,
  FiSearch,
  FiTrash2,
  FiTruck,
  FiX,
} from "react-icons/fi";
import type { VehicleCreate, VehicleUpdate } from "@/client";
import { VehiclesService } from "@/client";
import { toaster } from "@/components/ui/toaster";

const StyledSelect = chakra("select");

type FieldGroupProps = {
  label: string;
  helper?: string;
  required?: boolean;
  labelFor?: string;
  children: ReactNode;
} & StackProps;

const FieldGroup = ({
  label,
  helper,
  required,
  labelFor,
  children,
  ...stackProps
}: FieldGroupProps) => (
  <Stack gap={1} {...stackProps}>
    <chakra.label fontSize="sm" fontWeight="semibold" htmlFor={labelFor}>
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

const SELECT_BASE_PROPS = {
  borderWidth: "1px",
  borderColor: "gray.200",
  borderRadius: "md",
  bg: "white",
  px: 3,
  py: 2,
  _focusVisible: {
    outline: "2px solid",
    outlineColor: "purple.500",
  },
};

type VehicleStatus = "disponible" | "en_mission" | "maintenance" | "inactif";

const vehicleCategories = {
  ag1_camion_frigorifique: "Camion Frigorifique",
  ag2_camion_refrigere: "Camion Réfrigéré",
  bt1_camion_benne: "Camion-Benne",
  bt3_camion_malaxeur: "Camion Malaxeur",
  in1_camion_bache: "Camion Bâché",
  in3_camion_grue: "Camion-Grue",
  ch1_camion_citerne: "Camion-Citerne",
} as const;

type VehicleCategoryKey = keyof typeof vehicleCategories;

interface Vehicle {
  id: string;
  license_plate: string;
  category: VehicleCategoryKey;
  capacity_tons: number;
  status: VehicleStatus;
  current_km: number;
  brand: string;
  model: string;
  year: number;
}

interface VehicleFormState {
  license_plate: string;
  category: VehicleCategoryKey;
  capacity_tons: string;
  status: VehicleStatus;
  brand: string;
  model: string;
  year: string;
}

type ValidationErrors = Partial<Record<keyof VehicleFormState, string>>;

const statusConfig: Record<
  VehicleStatus,
  { label: string; color: string; icon: ComponentType }
> = {
  disponible: { label: "Disponible", color: "green", icon: FiCheckCircle },
  en_mission: { label: "En Mission", color: "blue", icon: FiTruck },
  maintenance: { label: "Maintenance", color: "orange", icon: FiAlertCircle },
  inactif: { label: "Inactif", color: "red", icon: FiAlertCircle },
};

const INITIAL_FORM: VehicleFormState = {
  license_plate: "",
  category: "ag1_camion_frigorifique",
  capacity_tons: "",
  status: "disponible",
  brand: "",
  model: "",
  year: String(new Date().getFullYear()),
};

const VehicleManagementPage = () => {
  const { open, onOpen, onClose } = useDisclosure();
  const [vehicles, setVehicles] = useState<Vehicle[]>([
    {
      id: "1",
      license_plate: "16-12345-ORN",
      category: "ag1_camion_frigorifique",
      capacity_tons: 12,
      status: "disponible",
      current_km: 45000,
      brand: "Mercedes",
      model: "Actros",
      year: 2020,
    },
    {
      id: "2",
      license_plate: "31-67890-CST",
      category: "bt1_camion_benne",
      capacity_tons: 18,
      status: "en_mission",
      current_km: 78000,
      brand: "Volvo",
      model: "FH16",
      year: 2019,
    },
    {
      id: "3",
      license_plate: "16-54321-ORN",
      category: "in1_camion_bache",
      capacity_tons: 10,
      status: "disponible",
      current_km: 32000,
      brand: "Renault",
      model: "T High",
      year: 2021,
    },
  ]);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState<"all" | VehicleStatus>(
    "all"
  );
  const [editingVehicle, setEditingVehicle] = useState<Vehicle | null>(null);
  const [formData, setFormData] = useState<VehicleFormState>(INITIAL_FORM);
  const [errors, setErrors] = useState<ValidationErrors>({});
  const formBaseId = "vehicle-form";
  const fieldIds = {
    license: `${formBaseId}-license`,
    category: `${formBaseId}-category`,
    capacity: `${formBaseId}-capacity`,
    status: `${formBaseId}-status`,
    brand: `${formBaseId}-brand`,
    model: `${formBaseId}-model`,
    year: `${formBaseId}-year`,
  };

  const filteredVehicles = useMemo(() => {
    return vehicles.filter((vehicle) => {
      const match = searchTerm.toLowerCase();
      const matchesSearch =
        vehicle.license_plate.toLowerCase().includes(match) ||
        vehicle.brand.toLowerCase().includes(match);
      const matchesStatus =
        filterStatus === "all" || vehicle.status === filterStatus;
      return matchesSearch && matchesStatus;
    });
  }, [vehicles, searchTerm, filterStatus]);

  const stats = useMemo(
    () => ({
      total: vehicles.length,
      available: vehicles.filter((v) => v.status === "disponible").length,
      in_mission: vehicles.filter((v) => v.status === "en_mission").length,
      maintenance: vehicles.filter((v) => v.status === "maintenance").length,
    }),
    [vehicles]
  );

  const resetForm = () => {
    setEditingVehicle(null);
    setFormData(INITIAL_FORM);
    setErrors({});
  };

  const updateField = <Key extends keyof VehicleFormState>(
    key: Key,
    value: VehicleFormState[Key]
  ) => {
    // Clear error for this field when user starts typing
    setErrors((prev) => {
      const newErrors = { ...prev };
      delete newErrors[key];
      return newErrors;
    });

    setFormData((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const validateForm = (): boolean => {
    const newErrors: ValidationErrors = {};

    // License plate validation (Algerian format: NNNNN-DDD-DD)
    if (!formData.license_plate.trim()) {
      newErrors.license_plate = "Veuillez saisir le matricule du véhicule";
    } else if (!/^\d{5}-\d{3}-\d{2}$/.test(formData.license_plate.trim())) {
      newErrors.license_plate =
        "Format attendu: *****-***-** (ex: 12345-678-90)";
    }

    // Capacity validation
    const capacity = Number(formData.capacity_tons);
    if (!formData.capacity_tons.trim()) {
      newErrors.capacity_tons = "Veuillez saisir la capacité du véhicule";
    } else if (Number.isNaN(capacity) || capacity <= 0) {
      newErrors.capacity_tons = "La capacité doit être un nombre positif";
    } else if (capacity > 100) {
      newErrors.capacity_tons = "La capacité ne peut pas dépasser 100 tonnes";
    }

    // Brand validation (optional but if provided, validate)
    if (formData.brand.trim() && formData.brand.trim().length < 2) {
      newErrors.brand =
        "Le nom de la marque doit contenir au moins 2 caractères";
    }

    // Model validation (optional but if provided, validate)
    if (formData.model.trim() && formData.model.trim().length < 2) {
      newErrors.model = "Le nom du modèle doit contenir au moins 2 caractères";
    }

    // Year validation
    const year = Number(formData.year);
    const currentYear = new Date().getFullYear();
    if (!formData.year.trim()) {
      newErrors.year = "Veuillez saisir l'année du véhicule";
    } else if (Number.isNaN(year) || year < 1900) {
      newErrors.year = "L'année doit être supérieure à 1900";
    } else if (year > currentYear + 1) {
      newErrors.year = `L'année ne peut pas dépasser ${currentYear + 1}`;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      toaster.error({
        title: "Erreur de saisie",
        description: "Veuillez corriger les erreurs dans le formulaire",
        meta: { closable: true, color: "red.solid" },
      });
      return;
    }

    const normalizedData = {
      ...formData,
      capacity_tons: Number(formData.capacity_tons) || 0,
      year: Number(formData.year) || new Date().getFullYear(),
    };

    try {
      if (editingVehicle) {
        // Update existing vehicle
        await VehiclesService.updateVehicle({
          vehicleId: editingVehicle.id,
          requestBody: normalizedData as VehicleUpdate,
        });
        setVehicles((prev) =>
          prev.map((vehicle) =>
            vehicle.id === editingVehicle.id
              ? { ...vehicle, ...normalizedData }
              : vehicle
          )
        );
        toaster.success({
          title: "Véhicule mis à jour",
          description: "Les informations ont été enregistrées",
          meta: { closable: true, color: "purple.solid" },
        });
      } else {
        // Create new vehicle
        const createdVehicle = await VehiclesService.createVehicle({
          requestBody: normalizedData as VehicleCreate,
        });
        // Cast to Vehicle type for local state
        setVehicles((prev) => [...prev, createdVehicle as unknown as Vehicle]);
        toaster.success({
          title: "Véhicule ajouté",
          description: "La flotte a été mise à jour",
          meta: { closable: true, color: "purple.solid" },
        });
      }
      handleClose();
    } catch (error: any) {
      const errorMsg =
        error?.response?.body?.detail ||
        error?.message ||
        "Une erreur est survenue";
      toaster.error({
        title: "Erreur lors de l'enregistrement",
        description: String(errorMsg),
        meta: { closable: true, color: "red.solid" },
      });
    }
  };

  const handleEdit = (vehicle: Vehicle) => {
    setEditingVehicle(vehicle);
    setFormData({
      license_plate: vehicle.license_plate,
      category: vehicle.category,
      capacity_tons: String(vehicle.capacity_tons),
      status: vehicle.status,
      brand: vehicle.brand,
      model: vehicle.model,
      year: String(vehicle.year),
    });
    onOpen();
  };

  const handleDelete = async (vehicleId: string) => {
    try {
      await VehiclesService.deleteVehicle({ vehicleId });
      setVehicles((prev) => prev.filter((vehicle) => vehicle.id !== vehicleId));
      toaster.success({
        title: "Véhicule supprimé",
        description: "Le véhicule a été retiré de la flotte",
        meta: { closable: true, color: "purple.solid" },
      });
    } catch (error: any) {
      const errorMsg =
        error?.response?.body?.detail ||
        error?.message ||
        "Impossible de supprimer le véhicule";
      toaster.error({
        title: "Erreur lors de la suppression",
        description: String(errorMsg),
        meta: { closable: true, color: "red.solid" },
      });
    }
  };

  return (
    <Container maxW="full" py={8} px={6}>
      <Flex justifyContent="space-between" alignItems="center" mb={8}>
        <Box>
          <Heading
            size="xl"
            mb={2}
            bgGradient="linear(to-r, purple.400, pink.500)"
            bgClip="text"
          >
            Gestion des Véhicules
          </Heading>
          <Text color="gray.600">Gérez votre flotte de véhicules</Text>
        </Box>
        <Button
          colorScheme="purple"
          size="lg"
          onClick={onOpen}
          borderRadius="xl"
        >
          <Flex align="center" gap={2}>
            <FiPlus />
            Ajouter un Véhicule
          </Flex>
        </Button>
      </Flex>

      <SimpleGrid columns={{ base: 1, md: 4 }} gap={6} mb={8}>
        <StatCard label="Total Flotte" value={stats.total} color="purple.500" />
        <StatCard
          label="Disponibles"
          value={stats.available}
          color="green.500"
        />
        <StatCard
          label="En Mission"
          value={stats.in_mission}
          color="blue.500"
        />
        <StatCard
          label="Maintenance"
          value={stats.maintenance}
          color="orange.500"
        />
      </SimpleGrid>

      <CardRoot variant="elevated" borderRadius="xl" mb={6}>
        <CardBody>
          <Flex gap={4} flexWrap="wrap">
            <InputGroup
              flex={1}
              minW="250px"
              startElement={<FiSearch color="gray.500" />}
              startElementProps={{ pointerEvents: "none" }}
            >
              <Input
                placeholder="Rechercher par matricule ou marque..."
                value={searchTerm}
                onChange={(event: ChangeEvent<HTMLInputElement>) =>
                  setSearchTerm(event.target.value)
                }
              />
            </InputGroup>
            <StyledSelect
              maxW="200px"
              value={filterStatus}
              onChange={(event: ChangeEvent<HTMLSelectElement>) =>
                setFilterStatus(event.target.value as VehicleStatus | "all")
              }
              {...SELECT_BASE_PROPS}
            >
              <option value="all">Tous les statuts</option>
              <option value="disponible">Disponible</option>
              <option value="en_mission">En Mission</option>
              <option value="maintenance">Maintenance</option>
              <option value="inactif">Inactif</option>
            </StyledSelect>
          </Flex>
        </CardBody>
      </CardRoot>

      <CardRoot variant="elevated" borderRadius="xl">
        <CardBody p={0}>
          <Box overflowX="auto">
            <TableRoot>
              <TableHeader bg="gray.50">
                <TableRow>
                  <TableColumnHeader>Matricule</TableColumnHeader>
                  <TableColumnHeader>Catégorie</TableColumnHeader>
                  <TableColumnHeader>Capacité</TableColumnHeader>
                  <TableColumnHeader>Marque/Modèle</TableColumnHeader>
                  <TableColumnHeader>Kilométrage</TableColumnHeader>
                  <TableColumnHeader>Statut</TableColumnHeader>
                  <TableColumnHeader textAlign="right">
                    Actions
                  </TableColumnHeader>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredVehicles.map((vehicle) => {
                  const statusInfo = statusConfig[vehicle.status];
                  const StatusIcon = statusInfo.icon;
                  return (
                    <TableRow key={vehicle.id} _hover={{ bg: "gray.50" }}>
                      <TableCell fontWeight="medium">
                        {vehicle.license_plate}
                      </TableCell>
                      <TableCell>
                        <Text fontSize="sm">
                          {vehicleCategories[vehicle.category]}
                        </Text>
                      </TableCell>
                      <TableCell>{vehicle.capacity_tons} T</TableCell>
                      <TableCell>
                        <Text fontSize="sm">
                          {vehicle.brand} {vehicle.model}
                        </Text>
                        <Text fontSize="xs" color="gray.500">
                          {vehicle.year}
                        </Text>
                      </TableCell>
                      <TableCell>
                        {vehicle.current_km.toLocaleString()} km
                      </TableCell>
                      <TableCell>
                        <Badge
                          colorScheme={statusInfo.color}
                          display="flex"
                          alignItems="center"
                          gap={1}
                          w="fit-content"
                        >
                          <StatusIcon />
                          {statusInfo.label}
                        </Badge>
                      </TableCell>
                      <TableCell textAlign="right">
                        <MenuRoot>
                          <MenuTrigger asChild>
                            <chakra.button
                              aria-label="Ouvrir les actions"
                              bg="transparent"
                              _hover={{ bg: "gray.100" }}
                              p={2}
                              borderRadius="md"
                              cursor="pointer"
                              display="inline-flex"
                              alignItems="center"
                              justifyContent="center"
                            >
                              <FiMoreVertical />
                            </chakra.button>
                          </MenuTrigger>
                          <MenuContent minW="150px">
                            <MenuItem
                              value={`edit-${vehicle.id}`}
                              onClick={() => handleEdit(vehicle)}
                            >
                              <Flex align="center" gap={2}>
                                <FiEdit2 />
                                Modifier
                              </Flex>
                            </MenuItem>
                            <MenuItem
                              value={`delete-${vehicle.id}`}
                              color="red.500"
                              onClick={() => handleDelete(vehicle.id)}
                            >
                              <Flex align="center" gap={2}>
                                <FiTrash2 />
                                Supprimer
                              </Flex>
                            </MenuItem>
                          </MenuContent>
                        </MenuRoot>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </TableRoot>
          </Box>
        </CardBody>
      </CardRoot>

      <DialogRoot
        open={open}
        onOpenChange={({ open }) => {
          if (!open) {
            handleClose();
          }
        }}
      >
        <DialogBackdrop />
        <DialogPositioner>
          <DialogContent
            borderRadius="xl"
            maxW="3xl"
            w="full"
            px={{ base: 4, md: 6 }}
            py={6}
          >
            <DialogHeader
              display="flex"
              alignItems="center"
              justifyContent="space-between"
              gap={3}
              px={0}
              pb={3}
            >
              <DialogTitle fontSize="lg" fontWeight="semibold" color="gray.900">
                {editingVehicle
                  ? "Modifier le Véhicule"
                  : "Ajouter un Véhicule"}
              </DialogTitle>
              <DialogCloseTrigger asChild>
                <IconButton aria-label="Fermer" variant="ghost" size="sm">
                  <FiX />
                </IconButton>
              </DialogCloseTrigger>
            </DialogHeader>
            <DialogBody px={0} pb={6}>
              <SimpleGrid columns={{ base: 1, md: 2 }} gap={4}>
                <FieldGroup
                  label="Matricule"
                  labelFor={fieldIds.license}
                  required
                >
                  <Input
                    id={fieldIds.license}
                    value={formData.license_plate}
                    onChange={(event: ChangeEvent<HTMLInputElement>) =>
                      updateField(
                        "license_plate",
                        event.target.value.toUpperCase()
                      )
                    }
                    placeholder="*****-***-**"
                    _invalid={errors.license_plate ? {} : undefined}
                  />
                  {errors.license_plate && (
                    <Text color="red.500" fontSize="sm" mt={1}>
                      {errors.license_plate}
                    </Text>
                  )}
                </FieldGroup>
                <FieldGroup
                  label="Catégorie"
                  labelFor={fieldIds.category}
                  required
                >
                  <StyledSelect
                    id={fieldIds.category}
                    value={formData.category}
                    onChange={(event: ChangeEvent<HTMLSelectElement>) =>
                      setFormData((prev) => ({
                        ...prev,
                        category: event.target.value as VehicleCategoryKey,
                      }))
                    }
                    {...SELECT_BASE_PROPS}
                  >
                    {Object.entries(vehicleCategories).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </StyledSelect>
                </FieldGroup>
                <FieldGroup
                  label="Capacité (T)"
                  labelFor={fieldIds.capacity}
                  required
                >
                  <Input
                    id={fieldIds.capacity}
                    type="number"
                    value={formData.capacity_tons}
                    onChange={(event: ChangeEvent<HTMLInputElement>) =>
                      updateField("capacity_tons", event.target.value)
                    }
                    placeholder="Ex: 12"
                    _invalid={errors.capacity_tons ? {} : undefined}
                  />
                  {errors.capacity_tons && (
                    <Text color="red.500" fontSize="sm" mt={1}>
                      {errors.capacity_tons}
                    </Text>
                  )}
                </FieldGroup>
                <FieldGroup label="Statut" labelFor={fieldIds.status} required>
                  <StyledSelect
                    id={fieldIds.status}
                    value={formData.status}
                    onChange={(event: ChangeEvent<HTMLSelectElement>) =>
                      setFormData((prev) => ({
                        ...prev,
                        status: event.target.value as VehicleStatus,
                      }))
                    }
                    {...SELECT_BASE_PROPS}
                  >
                    <option value="disponible">Disponible</option>
                    <option value="en_mission">En Mission</option>
                    <option value="maintenance">Maintenance</option>
                    <option value="inactif">Inactif</option>
                  </StyledSelect>
                </FieldGroup>
                <FieldGroup label="Marque" labelFor={fieldIds.brand}>
                  <Input
                    id={fieldIds.brand}
                    value={formData.brand}
                    onChange={(event: ChangeEvent<HTMLInputElement>) =>
                      updateField("brand", event.target.value)
                    }
                    placeholder="Mercedes"
                    _invalid={errors.brand ? {} : undefined}
                  />
                  {errors.brand && (
                    <Text color="red.500" fontSize="sm" mt={1}>
                      {errors.brand}
                    </Text>
                  )}
                </FieldGroup>
                <FieldGroup label="Modèle" labelFor={fieldIds.model}>
                  <Input
                    id={fieldIds.model}
                    value={formData.model}
                    onChange={(event: ChangeEvent<HTMLInputElement>) =>
                      updateField("model", event.target.value)
                    }
                    placeholder="Actros"
                    _invalid={errors.model ? {} : undefined}
                  />
                  {errors.model && (
                    <Text color="red.500" fontSize="sm" mt={1}>
                      {errors.model}
                    </Text>
                  )}
                </FieldGroup>
                <FieldGroup label="Année" labelFor={fieldIds.year}>
                  <Input
                    id={fieldIds.year}
                    type="number"
                    value={formData.year}
                    onChange={(event: ChangeEvent<HTMLInputElement>) =>
                      updateField("year", event.target.value)
                    }
                    placeholder="2021"
                    _invalid={errors.year ? {} : undefined}
                  />
                  {errors.year && (
                    <Text color="red.500" fontSize="sm" mt={1}>
                      {errors.year}
                    </Text>
                  )}
                </FieldGroup>
              </SimpleGrid>
            </DialogBody>
            <DialogFooter px={0} gap={3} justifyContent="flex-end">
              <Button variant="ghost" onClick={handleClose}>
                Annuler
              </Button>
              <Button colorScheme="purple" onClick={handleSubmit}>
                {editingVehicle ? "Mettre à jour" : "Ajouter"}
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
  value: number;
  color: string;
}

const StatCard = ({ label, value, color }: StatCardProps) => (
  <CardRoot variant="elevated" borderRadius="xl">
    <CardBody>
      <Text fontSize="sm" color="gray.600" mb={1}>
        {label}
      </Text>
      <Text fontSize="3xl" fontWeight="bold" color={color}>
        {value}
      </Text>
    </CardBody>
  </CardRoot>
);

export default VehicleManagementPage;
