import {
  Badge,
  Box,
  Button,
  CardBody,
  CardHeader,
  CardRoot,
  Container,
  chakra,
  Flex,
  Heading,
  Input,
  Separator,
  SimpleGrid,
  Spinner,
  Stack,
  Text,
  Textarea,
} from "@chakra-ui/react"
import { type ChangeEvent, type ReactNode, useEffect, useState } from "react"
import { FiBriefcase, FiMapPin, FiPhone, FiUser } from "react-icons/fi"
import type { IconType } from "react-icons/lib"

import type {
  ActivitySector,
  CompanyPublic,
  CompanyType,
  CompanyUpdate,
  PartnerType,
} from "@/client"
import CompanyRegistrationForm from "@/components/Company/CompanyRegistrationForm"
import { useCompany } from "@/hooks/useCompany"

interface CompanyFormState {
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
  logo_url: string
}

const COMPANY_TYPE_OPTIONS: Array<{ value: CompanyType; label: string }> = [
  { value: "production", label: "Production" },
  { value: "negoce", label: "Négoce" },
  { value: "service", label: "Services" },
]

const PARTNER_TYPE_OPTIONS: Array<{ value: PartnerType; label: string }> = [
  { value: "entreprise", label: "Entreprise" },
  { value: "prestataire_logistique", label: "Prestataire Logistique" },
]

const ACTIVITY_SECTOR_OPTIONS: Array<{ value: ActivitySector; label: string }> =
  [
    { value: "agroalimentaire", label: "Agroalimentaire" },
    { value: "construction_btp", label: "Construction & BTP" },
    { value: "industriel_manufacturier", label: "Industrie & Manufactures" },
    { value: "chimique_petrochimique", label: "Chimie & Pétrochimie" },
    { value: "agricole_rural", label: "Agricole & Rural" },
    { value: "logistique_messagerie", label: "Logistique & Messagerie" },
    { value: "medical_parapharmaceutique", label: "Médical & Parapharma" },
    { value: "hygiene_dechets_environnement", label: "Hygiène & Déchets" },
    { value: "energie_ressources_naturelles", label: "Énergie" },
    { value: "logistique_speciale", label: "Logistique Spéciale" },
    { value: "autre", label: "Autre" },
  ]

const INITIAL_FORM: CompanyFormState = {
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
  logo_url: "",
}

const toFormState = (company: CompanyPublic): CompanyFormState => ({
  company_name: company.company_name,
  nis: company.nis,
  nif: company.nif,
  headquarters_address: company.headquarters_address,
  company_type: company.company_type,
  activity_sector: company.activity_sector,
  sector_specification: company.sector_specification ?? "",
  partner_type: company.partner_type,
  legal_representative_name: company.legal_representative_name,
  legal_representative_contact: company.legal_representative_contact,
  logo_url: company.logo_url ?? "",
})

const normalizeUpdatePayload = (state: CompanyFormState): CompanyUpdate => ({
  company_name: state.company_name || undefined,
  headquarters_address: state.headquarters_address || undefined,
  company_type: state.company_type || undefined,
  activity_sector: state.activity_sector || undefined,
  sector_specification: state.sector_specification || undefined,
  partner_type: state.partner_type || undefined,
  legal_representative_name: state.legal_representative_name || undefined,
  legal_representative_contact: state.legal_representative_contact || undefined,
  logo_url: state.logo_url || undefined,
})

const StyledSelect = chakra("select")

const FieldGroup = ({
  label,
  helper,
  required,
  children,
}: {
  label: string
  helper?: string
  required?: boolean
  children: ReactNode
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
)

const CompanyProfile = () => {
  const {
    company,
    isLoading,
    isCreating,
    isUpdating,
    createCompany,
    updateCompany,
  } = useCompany()
  const [formState, setFormState] = useState<CompanyFormState>(
    company ? toFormState(company) : INITIAL_FORM,
  )

  useEffect(() => {
    if (company) {
      setFormState(toFormState(company))
      return
    }
    setFormState(INITIAL_FORM)
  }, [company])

  if (isLoading) {
    return (
      <Flex align="center" justify="center" minH="60vh">
        <Spinner size="xl" />
      </Flex>
    )
  }

  const isSubmitting = isCreating || isUpdating

  if (!company) {
    return (
      <CompanyRegistrationForm
        onSubmit={async (payload) => {
          await createCompany(payload)
        }}
        isSubmitting={isCreating}
        showSuccessToast={false}
      />
    )
  }

  const handleChange = <Key extends keyof CompanyFormState>(
    key: Key,
    value: CompanyFormState[Key],
  ) => {
    setFormState((prev) => ({
      ...prev,
      [key]: value,
    }))
  }

  const handleSubmit = async () => {
    await updateCompany(normalizeUpdatePayload(formState))
  }

  const isFormValid =
    Boolean(formState.company_name.trim()) &&
    Boolean(formState.nis.trim()) &&
    Boolean(formState.nif.trim()) &&
    Boolean(formState.headquarters_address.trim()) &&
    Boolean(formState.legal_representative_name.trim()) &&
    Boolean(formState.legal_representative_contact.trim())

  return (
    <Container maxW="6xl" py={10}>
      <Flex
        justify="space-between"
        align={{ base: "flex-start", md: "center" }}
        mb={10}
        direction={{ base: "column", md: "row" }}
        gap={4}
      >
        <Box>
          <Heading size="xl" mb={2}>
            Profil Entreprise
          </Heading>
          <Text color="gray.600">
            Centralisez les informations légales de votre société pour générer
            des documents conformes.
          </Text>
        </Box>
        {company && (
          <Badge colorScheme="green" px={4} py={2} borderRadius="full">
            Profil complété
          </Badge>
        )}
      </Flex>

      {company && (
        <CardRoot borderRadius="2xl" mb={8} variant="elevated">
          <CardHeader>
            <Heading size="md">Informations enregistrées</Heading>
          </CardHeader>
          <CardBody>
            <SimpleGrid columns={{ base: 1, md: 2 }} gap={6}>
              <InfoTile
                icon={FiBriefcase}
                label="Raison sociale"
                value={company.company_name}
              />
              <InfoTile
                icon={FiUser}
                label="Représentant"
                value={company.legal_representative_name}
              />
              <InfoTile
                icon={FiPhone}
                label="Contact"
                value={company.legal_representative_contact}
              />
              <InfoTile
                icon={FiMapPin}
                label="Adresse"
                value={company.headquarters_address}
              />
            </SimpleGrid>
          </CardBody>
        </CardRoot>
      )}

      <CardRoot borderRadius="2xl" variant="outline">
        <CardHeader>
          <Heading size="md">
            {company ? "Mettre à jour le profil" : "Créer votre profil"}
          </Heading>
          <Text color="gray.600" mt={2}>
            Ces informations seront utilisées pour les déclarations
            administratives et le suivi logistique.
          </Text>
        </CardHeader>
        <CardBody>
          <SimpleGrid columns={{ base: 1, md: 2 }} gap={6}>
            <FieldGroup label="Raison sociale" required>
              <Input
                value={formState.company_name}
                onChange={(event) =>
                  handleChange("company_name", event.target.value)
                }
              />
            </FieldGroup>
            <FieldGroup label="Représentant légal" required>
              <Input
                value={formState.legal_representative_name}
                onChange={(event) =>
                  handleChange("legal_representative_name", event.target.value)
                }
              />
            </FieldGroup>
            <FieldGroup label="NIS" required>
              <Input
                value={formState.nis}
                onChange={(event) => handleChange("nis", event.target.value)}
              />
            </FieldGroup>
            <FieldGroup label="NIF" required>
              <Input
                value={formState.nif}
                onChange={(event) => handleChange("nif", event.target.value)}
              />
            </FieldGroup>
            <FieldGroup label="Adresse du siège" required>
              <Textarea
                rows={3}
                value={formState.headquarters_address}
                onChange={(event) =>
                  handleChange("headquarters_address", event.target.value)
                }
              />
            </FieldGroup>
            <FieldGroup label="Contact" required>
              <Input
                value={formState.legal_representative_contact}
                onChange={(event) =>
                  handleChange(
                    "legal_representative_contact",
                    event.target.value,
                  )
                }
              />
            </FieldGroup>
          </SimpleGrid>

          <Separator my={8} />

          <SimpleGrid columns={{ base: 1, md: 3 }} gap={6}>
            <FieldGroup label="Type d'entreprise" required>
              <StyledSelect
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
                value={formState.company_type}
                onChange={(event: ChangeEvent<HTMLSelectElement>) =>
                  handleChange(
                    "company_type",
                    event.target.value as CompanyType,
                  )
                }
              >
                {COMPANY_TYPE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </StyledSelect>
            </FieldGroup>
            <FieldGroup label="Secteur d'activité" required>
              <StyledSelect
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
                value={formState.activity_sector}
                onChange={(event: ChangeEvent<HTMLSelectElement>) =>
                  handleChange(
                    "activity_sector",
                    event.target.value as ActivitySector,
                  )
                }
              >
                {ACTIVITY_SECTOR_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </StyledSelect>
            </FieldGroup>
            <FieldGroup label="Type de partenaire" required>
              <StyledSelect
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
                value={formState.partner_type}
                onChange={(event: ChangeEvent<HTMLSelectElement>) =>
                  handleChange(
                    "partner_type",
                    event.target.value as PartnerType,
                  )
                }
              >
                {PARTNER_TYPE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </StyledSelect>
            </FieldGroup>
          </SimpleGrid>

          <SimpleGrid columns={{ base: 1, md: 2 }} gap={6} mt={6}>
            <FieldGroup label="Spécificités secteur">
              <Textarea
                rows={3}
                value={formState.sector_specification}
                onChange={(event) =>
                  handleChange("sector_specification", event.target.value)
                }
              />
            </FieldGroup>
            <FieldGroup label="Logo (URL)">
              <Input
                value={formState.logo_url}
                onChange={(event) =>
                  handleChange("logo_url", event.target.value)
                }
                placeholder="https://..."
              />
            </FieldGroup>
          </SimpleGrid>

          <Button
            colorScheme="purple"
            mt={8}
            w={{ base: "full", md: "auto" }}
            onClick={handleSubmit}
            disabled={!isFormValid}
            loading={isSubmitting}
          >
            {company ? "Enregistrer les modifications" : "Créer le profil"}
          </Button>
        </CardBody>
      </CardRoot>
    </Container>
  )
}

interface InfoTileProps {
  icon: IconType
  label: string
  value: string
}

const InfoTile = ({ icon: Icon, label, value }: InfoTileProps) => (
  <Stack gap={1} borderWidth="1px" borderRadius="lg" p={4}>
    <Flex align="center" gap={2} color="gray.600">
      <Icon />
      <Text fontSize="sm">{label}</Text>
    </Flex>
    <Text fontWeight="semibold">{value}</Text>
  </Stack>
)

export default CompanyProfile
