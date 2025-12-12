import {
  Badge,
  Box,
  Button,
  CardBody,
  CardRoot,
  Container,
  chakra,
  Flex,
  Heading,
  HStack,
  Icon,
  Input,
  Stack,
  type StackProps,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react"
import { type ReactNode, useMemo, useState } from "react"
import { FiBriefcase, FiCheckCircle, FiMapPin, FiUser } from "react-icons/fi"
import type {
  ActivitySector,
  CompanyCreate,
  CompanyType,
  PartnerType,
} from "@/client"
import { toaster } from "@/components/ui/toaster"
import { getErrorMessage } from "@/utils"

type CompanyRegistrationFormState = {
  company_name: string
  nis: string
  nif: string
  headquarters_address: string
  company_type: CompanyType
  activity_sector: ActivitySector
  sector_specification: string
  partner_type: PartnerType
  legal_representative_name: string
  legal_representative_contact: string
}

type ValidationErrors = Partial<
  Record<keyof CompanyRegistrationFormState, string>
>

interface CompanyRegistrationFormProps {
  onSubmit: (payload: CompanyCreate) => Promise<void>
  isSubmitting?: boolean
  showSuccessToast?: boolean
}

const INITIAL_STATE: CompanyRegistrationFormState = {
  company_name: "",
  nis: "",
  nif: "",
  headquarters_address: "",
  company_type: "production",
  activity_sector: "agroalimentaire",
  sector_specification: "",
  partner_type: "entreprise",
  legal_representative_name: "",
  legal_representative_contact: "",
}

const COMPANY_TYPES: Record<CompanyType, string> = {
  production: "Production",
  negoce: "Négoce",
  service: "Service",
}

const ACTIVITY_SECTORS: Record<ActivitySector, string> = {
  agroalimentaire: "Agroalimentaire",
  construction_btp: "Construction et BTP",
  industriel_manufacturier: "Industriel et Manufacturier",
  chimique_petrochimique: "Chimique et Pétrochimique",
  agricole_rural: "Agricole et Rural",
  logistique_messagerie: "Logistique et Messagerie",
  medical_parapharmaceutique: "Médical et Parapharmaceutique",
  hygiene_dechets_environnement: "Hygiène, Déchets et Environnement",
  energie_ressources_naturelles: "Énergie et Ressources Naturelles",
  logistique_speciale: "Logistique Spéciale",
  autre: "Autre",
}

const StyledSelect = chakra("select")

type FieldGroupProps = {
  label: string
  helper?: string
  required?: boolean
  children: ReactNode
} & StackProps

const FieldGroup = ({
  label,
  helper,
  required,
  children,
  ...stackProps
}: FieldGroupProps) => (
  <Stack gap={1} {...stackProps}>
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
)

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
}

const CompanyRegistrationForm = ({
  onSubmit,
  isSubmitting = false,
  showSuccessToast = true,
}: CompanyRegistrationFormProps) => {
  const [step, setStep] = useState(1)
  const [formData, setFormData] =
    useState<CompanyRegistrationFormState>(INITIAL_STATE)
  const [errors, setErrors] = useState<ValidationErrors>({})

  const progressPercent = useMemo(() => (step / 3) * 100, [step])

  const updateField = <Key extends keyof CompanyRegistrationFormState>(
    key: Key,
    value: CompanyRegistrationFormState[Key],
  ) => {
    // Clear error for this field when user starts typing
    setErrors((prev) => {
      const newErrors = { ...prev }
      delete newErrors[key]
      return newErrors
    })

    setFormData((prev) => ({
      ...prev,
      [key]: value,
    }))
  }

  const validateStep1 = (): boolean => {
    const newErrors: ValidationErrors = {}

    // Company name validation
    if (!formData.company_name.trim()) {
      newErrors.company_name = "Veuillez saisir le nom de votre entreprise"
    } else if (formData.company_name.trim().length < 3) {
      newErrors.company_name = "Le nom doit contenir au moins 3 caractères"
    }

    // NIS validation
    if (!formData.nis.trim()) {
      newErrors.nis = "Le numéro NIS est obligatoire"
    } else if (!/^\d+$/.test(formData.nis)) {
      newErrors.nis = "Le NIS doit contenir uniquement des chiffres"
    } else if (formData.nis.length > 15) {
      newErrors.nis = "Le NIS ne peut pas dépasser 15 chiffres"
    }

    // NIF validation
    if (!formData.nif.trim()) {
      newErrors.nif = "Le numéro NIF est obligatoire"
    } else if (!/^\d+$/.test(formData.nif)) {
      newErrors.nif = "Le NIF doit contenir uniquement des chiffres"
    } else if (formData.nif.length < 15) {
      newErrors.nif = "Le NIF doit contenir au moins 15 chiffres"
    } else if (formData.nif.length > 20) {
      newErrors.nif = "Le NIF ne peut pas dépasser 20 chiffres"
    }

    // Address validation
    if (!formData.headquarters_address.trim()) {
      newErrors.headquarters_address =
        "Veuillez saisir l'adresse du siège social"
    } else if (formData.headquarters_address.trim().length < 10) {
      newErrors.headquarters_address =
        "L'adresse doit contenir au moins 10 caractères"
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const validateStep3 = (): boolean => {
    const newErrors: ValidationErrors = {}

    // Legal representative name validation
    if (!formData.legal_representative_name.trim()) {
      newErrors.legal_representative_name =
        "Veuillez saisir le nom du représentant légal"
    } else if (formData.legal_representative_name.trim().length < 3) {
      newErrors.legal_representative_name =
        "Le nom doit contenir au moins 3 caractères"
    } else if (!/^[a-zA-ZÀ-ÿ\s'-]+$/.test(formData.legal_representative_name)) {
      newErrors.legal_representative_name =
        "Le nom ne doit contenir que des lettres"
    }

    // Phone validation
    if (!formData.legal_representative_contact.trim()) {
      newErrors.legal_representative_contact =
        "Veuillez saisir le numéro de téléphone"
    } else {
      const cleaned = formData.legal_representative_contact.replace(
        /[\s-]/g,
        "",
      )
      if (!cleaned.startsWith("+213") && !cleaned.startsWith("0")) {
        newErrors.legal_representative_contact =
          "Le numéro doit commencer par +213 ou 0"
      } else if (cleaned.startsWith("+213") && cleaned.length !== 13) {
        newErrors.legal_representative_contact =
          "Format attendu: +213 suivi de 9 chiffres"
      } else if (cleaned.startsWith("0") && cleaned.length !== 10) {
        newErrors.legal_representative_contact =
          "Format attendu: 0 suivi de 9 chiffres"
      } else if (!/^\+?\d+$/.test(cleaned)) {
        newErrors.legal_representative_contact =
          "Le numéro doit contenir uniquement des chiffres"
      }
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }
  const nextStep = () => {
    if (step === 1 && !validateStep1()) {
      return
    }
    setStep((current) => Math.min(current + 1, 3))
  }
  const prevStep = () => setStep((current) => Math.max(current - 1, 1))

  const handleSubmit = async () => {
    // Validate step 3 before submitting
    if (!validateStep3()) {
      return
    }

    const payload: CompanyCreate = {
      ...formData,
      sector_specification: formData.sector_specification || undefined,
    }

    try {
      await onSubmit(payload)

      if (showSuccessToast) {
        toaster.success({
          title: "Entreprise créée avec succès!",
          description: "Votre profil d'entreprise a été enregistré.",
          meta: { closable: true, color: "green.solid" },
        })
      }
    } catch (error: any) {
      // Extract error message from backend
      const errorMessage = getErrorMessage(error)

      // Check for common business logic errors
      let title = "Erreur"
      let description = errorMessage

      if (
        errorMessage.toLowerCase().includes("nis") &&
        errorMessage.toLowerCase().includes("exist")
      ) {
        title = "NIS déjà utilisé"
        description =
          "Ce numéro NIS est déjà enregistré dans notre système. Veuillez vérifier votre saisie."
      } else if (
        errorMessage.toLowerCase().includes("nif") &&
        errorMessage.toLowerCase().includes("exist")
      ) {
        title = "NIF déjà utilisé"
        description =
          "Ce numéro NIF est déjà enregistré dans notre système. Veuillez vérifier votre saisie."
      } else if (
        errorMessage.toLowerCase().includes("company") &&
        errorMessage.toLowerCase().includes("exist")
      ) {
        title = "Entreprise déjà enregistrée"
        description = "Vous avez déjà un profil d'entreprise enregistré."
      } else if (errorMessage.toLowerCase().includes("credential")) {
        title = "Session expirée"
        description = "Votre session a expiré. Veuillez vous reconnecter."
      }

      toaster.error({
        title,
        description,
        meta: { closable: true, color: "red.solid" },
      })
    }
  }

  const isStepThreeValid =
    formData.legal_representative_name.trim().length >= 3 &&
    /^[a-zA-ZÀ-ÿ\s'-]+$/.test(formData.legal_representative_name) &&
    formData.legal_representative_contact.trim().length > 0

  const isNextDisabled = false // Allow clicking next, validation happens on nextStep()

  return (
    <Container maxW="4xl" py={8}>
      <Box textAlign="center" mb={8}>
        <Heading
          size="2xl"
          mb={2}
          bgGradient="linear(to-r, teal.400, blue.500)"
          bgClip="text"
        >
          Inscription Entreprise
        </Heading>
        <Text color="gray.600" fontSize="lg">
          Créez votre profil pour accéder à la plateforme
        </Text>
      </Box>

      <CardRoot variant="elevated" borderRadius="xl" mb={6}>
        <CardBody>
          <Flex alignItems="center" mb={4}>
            <Text fontSize="sm" fontWeight="medium" color="gray.600">
              Étape {step} sur 3
            </Text>
            <Badge ml="auto" colorScheme="teal" px={3} py={1}>
              {progressPercent.toFixed(0)}% complété
            </Badge>
          </Flex>
          <Box
            mt={2}
            borderRadius="full"
            bg="gray.200"
            height="8px"
            overflow="hidden"
          >
            <Box
              height="full"
              bgGradient="linear(to-r, teal.400, blue.500)"
              width={`${progressPercent}%`}
              transition="width 0.2s"
            />
          </Box>

          <HStack mt={4} gap={4}>
            <Flex alignItems="center" flex={1}>
              <Icon
                as={FiBriefcase}
                color={step >= 1 ? "teal.500" : "gray.300"}
                mr={2}
              />
              <Text
                fontSize="sm"
                color={step >= 1 ? "teal.600" : "gray.400"}
                fontWeight={step === 1 ? "bold" : "normal"}
              >
                Informations Générales
              </Text>
            </Flex>
            <Flex alignItems="center" flex={1}>
              <Icon
                as={FiMapPin}
                color={step >= 2 ? "teal.500" : "gray.300"}
                mr={2}
              />
              <Text
                fontSize="sm"
                color={step >= 2 ? "teal.600" : "gray.400"}
                fontWeight={step === 2 ? "bold" : "normal"}
              >
                Secteur d'Activité
              </Text>
            </Flex>
            <Flex alignItems="center" flex={1}>
              <Icon
                as={FiUser}
                color={step >= 3 ? "teal.500" : "gray.300"}
                mr={2}
              />
              <Text
                fontSize="sm"
                color={step >= 3 ? "teal.600" : "gray.400"}
                fontWeight={step === 3 ? "bold" : "normal"}
              >
                Représentant Légal
              </Text>
            </Flex>
          </HStack>
        </CardBody>
      </CardRoot>

      <CardRoot variant="elevated" borderRadius="xl">
        <CardBody p={8}>
          {step === 1 && (
            <VStack gap={6} align="stretch">
              <FieldGroup label="Nom de l'Entreprise" required>
                <Input
                  value={formData.company_name}
                  onChange={(event) =>
                    updateField("company_name", event.target.value)
                  }
                  placeholder="Ex: Entreprise Logistique Algérie"
                  size="lg"
                  _invalid={errors.company_name ? {} : undefined}
                />
                {errors.company_name && (
                  <Text color="red.500" fontSize="sm" mt={1}>
                    {errors.company_name}
                  </Text>
                )}
              </FieldGroup>

              <HStack gap={4} align={{ base: "stretch", md: "center" }}>
                <FieldGroup label="NIS (15 chiffres max)" required flex={1}>
                  <Input
                    value={formData.nis}
                    onChange={(event) => updateField("nis", event.target.value)}
                    placeholder="123456789012345"
                    maxLength={15}
                    _invalid={errors.nis ? {} : undefined}
                    size="lg"
                  />
                  {errors.nis && (
                    <Text color="red.500" fontSize="sm" mt={1}>
                      {errors.nis}
                    </Text>
                  )}
                </FieldGroup>

                <FieldGroup label="NIF (15-20 chiffres)" required flex={1}>
                  <Input
                    value={formData.nif}
                    onChange={(event) => updateField("nif", event.target.value)}
                    placeholder="123456789012345678"
                    minLength={15}
                    maxLength={20}
                    _invalid={errors.nif ? {} : undefined}
                    size="lg"
                  />
                  {errors.nif && (
                    <Text color="red.500" fontSize="sm" mt={1}>
                      {errors.nif}
                    </Text>
                  )}
                </FieldGroup>
              </HStack>

              <FieldGroup label="Adresse du Siège Social" required>
                <Textarea
                  value={formData.headquarters_address}
                  onChange={(event) =>
                    updateField("headquarters_address", event.target.value)
                  }
                  placeholder="Ex: Rue de la République, Oran, Algérie"
                  rows={3}
                  _invalid={errors.headquarters_address ? {} : undefined}
                  size="lg"
                />
                {errors.headquarters_address && (
                  <Text color="red.500" fontSize="sm" mt={1}>
                    {errors.headquarters_address}
                  </Text>
                )}
              </FieldGroup>

              <FieldGroup label="Type d'Entreprise" required>
                <StyledSelect
                  value={formData.company_type}
                  onChange={(event) =>
                    updateField(
                      "company_type",
                      event.target.value as CompanyType,
                    )
                  }
                  {...SELECT_BASE_PROPS}
                >
                  {Object.entries(COMPANY_TYPES).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </StyledSelect>
              </FieldGroup>
            </VStack>
          )}

          {step === 2 && (
            <VStack gap={6} align="stretch">
              <FieldGroup label="Secteur d'Activité Principal" required>
                <StyledSelect
                  value={formData.activity_sector}
                  onChange={(event) =>
                    updateField(
                      "activity_sector",
                      event.target.value as ActivitySector,
                    )
                  }
                  {...SELECT_BASE_PROPS}
                >
                  {Object.entries(ACTIVITY_SECTORS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </StyledSelect>
              </FieldGroup>

              <FieldGroup
                label="Spécification du Secteur (Optionnel)"
                helper="Précisez si votre activité implique des marchandises spécifiques"
              >
                <Input
                  value={formData.sector_specification}
                  onChange={(event) =>
                    updateField("sector_specification", event.target.value)
                  }
                  placeholder="Ex: Transport de produits frais et surgelés"
                  size="lg"
                />
              </FieldGroup>

              <FieldGroup label="Type de Partenaire" required>
                <StyledSelect
                  value={formData.partner_type}
                  onChange={(event) =>
                    updateField(
                      "partner_type",
                      event.target.value as PartnerType,
                    )
                  }
                  {...SELECT_BASE_PROPS}
                >
                  <option value="entreprise">Entreprise</option>
                  <option value="prestataire_logistique">
                    Prestataire Logistique
                  </option>
                </StyledSelect>
              </FieldGroup>

              <Box bg="blue.50" p={4} borderRadius="lg">
                <Text fontSize="sm" color="blue.700">
                  <strong>Note:</strong> Le secteur d'activité déterminera les
                  catégories de véhicules et de marchandises compatibles avec
                  votre entreprise lors de l'optimisation.
                </Text>
              </Box>
            </VStack>
          )}

          {step === 3 && (
            <VStack gap={6} align="stretch">
              <FieldGroup label="Nom du Représentant Légal" required>
                <Input
                  value={formData.legal_representative_name}
                  onChange={(event) =>
                    updateField("legal_representative_name", event.target.value)
                  }
                  placeholder="Ex: Ahmed Benali"
                  _invalid={errors.legal_representative_name ? {} : undefined}
                  size="lg"
                />
                {errors.legal_representative_name && (
                  <Text color="red.500" fontSize="sm" mt={1}>
                    {errors.legal_representative_name}
                  </Text>
                )}
              </FieldGroup>

              <FieldGroup label="Contact du Représentant" required>
                <Input
                  value={formData.legal_representative_contact}
                  onChange={(event) =>
                    updateField(
                      "legal_representative_contact",
                      event.target.value,
                    )
                  }
                  placeholder="Ex: +213 555 123 456"
                  _invalid={
                    errors.legal_representative_contact ? {} : undefined
                  }
                  size="lg"
                />
                {errors.legal_representative_contact && (
                  <Text color="red.500" fontSize="sm" mt={1}>
                    {errors.legal_representative_contact}
                  </Text>
                )}
              </FieldGroup>

              <Box bg="green.50" p={4} borderRadius="lg">
                <Flex alignItems="start">
                  <Icon as={FiCheckCircle} color="green.600" mt={1} mr={3} />
                  <Box>
                    <Text
                      fontSize="sm"
                      fontWeight="bold"
                      color="green.800"
                      mb={1}
                    >
                      Prêt à valider
                    </Text>
                    <Text fontSize="sm" color="green.700">
                      Votre profil d'entreprise sera soumis pour vérification.
                      Vous recevrez une notification une fois validé.
                    </Text>
                  </Box>
                </Flex>
              </Box>
            </VStack>
          )}

          <HStack mt={8} justifyContent="space-between">
            <Button
              variant="ghost"
              onClick={prevStep}
              disabled={step === 1}
              size="lg"
            >
              Précédent
            </Button>

            {step < 3 ? (
              <Button
                colorScheme="teal"
                onClick={nextStep}
                size="lg"
                disabled={isNextDisabled}
              >
                Suivant
              </Button>
            ) : (
              <Button
                colorScheme="teal"
                onClick={handleSubmit}
                size="lg"
                disabled={!isStepThreeValid}
                loading={isSubmitting}
              >
                Créer l'Entreprise
              </Button>
            )}
          </HStack>
        </CardBody>
      </CardRoot>
    </Container>
  )
}

export default CompanyRegistrationForm
