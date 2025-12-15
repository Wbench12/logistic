import {
  Badge,
  Box,
  Button,
  CardBody,
  CardHeader,
  CardRoot,
  Container,
  Flex,
  Heading,
  HStack,
  Icon,
  Image,
  Input,
  Separator,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
} from "@chakra-ui/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import {
  FiBriefcase,
  FiCheckCircle,
  FiEdit2,
  FiMapPin,
  FiSave,
  FiShield,
  FiUser,
  FiX,
} from "react-icons/fi";

import { type ApiError, type CompanyUpdate, CompaniesService } from "@/client";
import { useCompany } from "@/hooks/useCompany";
import { Field } from "@/components/ui/field";
import { Toaster, toaster } from "@/components/ui/toaster";
import { handleError } from "@/utils";
import { SkeletonText, SkeletonCircle } from "@/components/ui/skeleton";

// Config Options
const COMPANY_TYPE_OPTIONS = [
  { value: "production", label: "Production" },
  { value: "negoce", label: "Négoce" },
  { value: "service", label: "Services" },
];

const PARTNER_TYPE_OPTIONS = [
  { value: "entreprise", label: "Entreprise" },
  { value: "prestataire_logistique", label: "Prestataire Logistique" },
];

const ACTIVITY_SECTOR_OPTIONS = [
  { value: "agroalimentaire", label: "Agroalimentaire" },
  { value: "construction_btp", label: "Construction & BTP" },
  { value: "industriel_manufacturier", label: "Industrie & Manufactures" },
  { value: "chimique_petrochimique", label: "Chimie & Pétrochimie" },
  { value: "agricole_rural", label: "Agricole & Rural" },
  { value: "logistique_messagerie", label: "Logistique & Messagerie" },
  { value: "autre", label: "Autre" },
];

const CompanyProfile = () => {
  const queryClient = useQueryClient();
  const { company, isLoading, refetchCompany } = useCompany();
  const [isEditing, setIsEditing] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<CompanyUpdate>();

  const logoUrlValue = watch("logo_url");

  // Sync form with data when loaded
  useEffect(() => {
    if (company) {
      reset(company);
    }
  }, [company, reset]);

  const mutation = useMutation({
    mutationFn: (data: CompanyUpdate) =>
      CompaniesService.updateCompanyMe({ requestBody: data }),
    onSuccess: () => {
      toaster.success({
        title: "Profil mis à jour",
        description: "Les modifications ont été enregistrées.",
      });
      setIsEditing(false);
      refetchCompany();
      queryClient.invalidateQueries({ queryKey: ["companyProfile"] });
    },
    onError: (err: ApiError) => handleError(err),
  });

  const onSubmit = (data: CompanyUpdate) => {
    mutation.mutate(data);
  };

  if (isLoading) {
    return <ProfileSkeleton />;
  }

  // If null (shouldn't happen due to layout modal, but safe guard)
  if (!company) return null;

  return (
    <Container maxW="container.xl" py={8} px={{ base: 4, md: 8 }}>
      <Toaster />

      {/* Header Banner */}
      <Box
        position="relative"
        h="200px"
        bgGradient="linear(to-r, brand.900, brand.700)"
        borderRadius="2xl"
        mb={16}
        boxShadow="md"
        overflow="visible"
      >
        <Box
          position="absolute"
          top="0"
          left="0"
          w="full"
          h="full"
          opacity="0.1"
          bgImage="url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iMSIgY3k9IjEiIHI9IjEiIGZpbGw9IiNmZmYiLz48L3N2Zz4=')"
        />

        {/* Logo Card */}
        <Box
          position="absolute"
          bottom="-50px"
          left={{ base: "50%", md: "40px" }}
          transform={{ base: "translateX(-50%)", md: "none" }}
          bg="bg.panel"
          p={2}
          borderRadius="2xl"
          boxShadow="lg"
          borderWidth="1px"
          borderColor="border.subtle"
        >
          <Image
            src={
              (isEditing ? logoUrlValue : company.logo_url) ??
              "https://placehold.co/128x128?text=Logo"
            }
            alt="Company Logo"
            boxSize="128px"
            objectFit="contain"
            borderRadius="xl"
            bg="white"
          />
        </Box>

        <Flex position="absolute" bottom={4} right={6}>
          {!isEditing && (
            <Button
              onClick={() => setIsEditing(true)}
              variant="surface"
              colorPalette="white"
              fontWeight="bold"
            >
              <FiEdit2 /> Modifier le profil
            </Button>
          )}
        </Flex>
      </Box>

      {/* Content Form */}
      <form onSubmit={handleSubmit(onSubmit)}>
        <Flex direction={{ base: "column", lg: "row" }} gap={8}>
          {/* Sidebar Info */}
          <Stack flex="1" gap={6} maxW={{ lg: "350px" }}>
            <CardRoot variant="elevated" borderRadius="xl" bg="bg.panel">
              <CardBody>
                {isEditing ? (
                  <Stack gap={4}>
                    <Field
                      label="Nom de l'entreprise"
                      required
                      invalid={!!errors.company_name}
                      errorText={errors.company_name?.message}
                    >
                      <Input
                        {...register("company_name", { required: "Requis" })}
                        fontWeight="bold"
                        fontSize="lg"
                      />
                    </Field>
                    <Field label="URL du Logo">
                      <Input
                        {...register("logo_url")}
                        placeholder="https://..."
                        fontSize="sm"
                      />
                    </Field>
                  </Stack>
                ) : (
                  <Box>
                    <Heading size="2xl" mb={2} color="fg.default">
                      {company.company_name}
                    </Heading>
                    <HStack mb={4}>
                      <Badge colorPalette="green" variant="solid">
                        <FiCheckCircle /> Vérifié
                      </Badge>
                      <Badge colorPalette="blue" variant="subtle">
                        {company.partner_type}
                      </Badge>
                    </HStack>
                    <Text color="fg.muted" fontSize="sm">
                      Membre depuis le{" "}
                      {new Date(company.created_at).toLocaleDateString()}
                    </Text>
                  </Box>
                )}

                <Separator my={6} borderColor="border.subtle" />

                <Heading
                  size="sm"
                  mb={4}
                  display="flex"
                  alignItems="center"
                  gap={2}
                  color="fg.default"
                >
                  <Icon as={FiUser} color="brand.500" /> Contact Principal
                </Heading>

                <Stack gap={4}>
                  <Field label="Représentant Légal" readOnly={!isEditing}>
                    <Input
                      {...register("legal_representative_name")}
                      variant={isEditing ? "outline" : "flushed"}
                      color="fg.default"
                    />
                  </Field>
                  <Field label="Téléphone" readOnly={!isEditing}>
                    <Input
                      {...register("legal_representative_contact")}
                      variant={isEditing ? "outline" : "flushed"}
                      color="fg.default"
                    />
                  </Field>
                </Stack>
              </CardBody>
            </CardRoot>
          </Stack>

          {/* Main Info */}
          <Stack flex="2" gap={6}>
            <CardRoot variant="elevated" borderRadius="xl" bg="bg.panel">
              <CardHeader>
                <Heading
                  size="md"
                  display="flex"
                  alignItems="center"
                  gap={2}
                  color="fg.default"
                >
                  <Icon as={FiShield} color="brand.500" /> Informations Légales
                </Heading>
              </CardHeader>
              <CardBody>
                <SimpleGrid columns={{ base: 1, md: 2 }} gap={6}>
                  <Field label="Numéro NIS" readOnly={!isEditing} required>
                    <Input
                      value={company.nis ?? ""}
                      readOnly
                      variant="flushed"
                      fontFamily="mono"
                    />
                  </Field>
                  <Field label="Numéro NIF" readOnly={!isEditing} required>
                    <Input
                      value={company.nif ?? ""}
                      readOnly
                      variant="flushed"
                      fontFamily="mono"
                    />
                  </Field>
                  <Box gridColumn={{ base: "auto", md: "1 / -1" }}>
                    <Field label="Adresse du Siège" readOnly={!isEditing}>
                      <HStack align="start" w="full">
                        {isEditing && (
                          <Icon as={FiMapPin} mt={2} color="gray.400" />
                        )}
                        <Textarea
                          {...register("headquarters_address", {
                            required: "Requis",
                          })}
                          variant={isEditing ? "outline" : "flushed"}
                          minH="80px"
                          resize="none"
                        />
                      </HStack>
                    </Field>
                  </Box>
                </SimpleGrid>
              </CardBody>
            </CardRoot>

            <CardRoot variant="elevated" borderRadius="xl" bg="bg.panel">
              <CardHeader>
                <Heading
                  size="md"
                  display="flex"
                  alignItems="center"
                  gap={2}
                  color="fg.default"
                >
                  <Icon as={FiBriefcase} color="brand.500" /> Activité &
                  Opérations
                </Heading>
              </CardHeader>
              <CardBody>
                <SimpleGrid columns={{ base: 1, md: 2 }} gap={6}>
                  <Field label="Type d'entreprise" readOnly={!isEditing}>
                    {isEditing ? (
                      <select
                        {...register("company_type")}
                        style={{
                          width: "100%",
                          padding: "10px",
                          borderRadius: "6px",
                          border: "1px solid #E2E8F0",
                          background: "transparent",
                        }}
                      >
                        {COMPANY_TYPE_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <Input
                        value={
                          COMPANY_TYPE_OPTIONS.find(
                            (o) => o.value === company.company_type
                          )?.label
                        }
                        readOnly
                        variant="flushed"
                      />
                    )}
                  </Field>
                  <Field label="Type de Partenaire" readOnly={!isEditing}>
                    {isEditing ? (
                      <select
                        {...register("partner_type")}
                        style={{
                          width: "100%",
                          padding: "10px",
                          borderRadius: "6px",
                          border: "1px solid #E2E8F0",
                          background: "transparent",
                        }}
                      >
                        {PARTNER_TYPE_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <Input
                        value={
                          PARTNER_TYPE_OPTIONS.find(
                            (o) => o.value === company.partner_type
                          )?.label
                        }
                        readOnly
                        variant="flushed"
                      />
                    )}
                  </Field>
                  <Field label="Secteur d'activité" readOnly={!isEditing}>
                    {isEditing ? (
                      <select
                        {...register("activity_sector")}
                        style={{
                          width: "100%",
                          padding: "10px",
                          borderRadius: "6px",
                          border: "1px solid #E2E8F0",
                          background: "transparent",
                        }}
                      >
                        {ACTIVITY_SECTOR_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <Input
                        value={
                          ACTIVITY_SECTOR_OPTIONS.find(
                            (o) => o.value === company.activity_sector
                          )?.label
                        }
                        readOnly
                        variant="flushed"
                      />
                    )}
                  </Field>
                  <Field label="Spécificité (Optionnel)" readOnly={!isEditing}>
                    <Input
                      {...register("sector_specification")}
                      placeholder="Ex: Transport de produits frais"
                      variant={isEditing ? "outline" : "flushed"}
                    />
                  </Field>
                </SimpleGrid>
              </CardBody>
            </CardRoot>

            {isEditing && (
              <Flex justify="end" gap={4} py={4}>
                <Button
                  variant="ghost"
                  size="lg"
                  onClick={() => {
                    reset(company);
                    setIsEditing(false);
                  }}
                >
                  <FiX /> Annuler
                </Button>
                <Button
                  type="submit"
                  colorPalette="brand"
                  size="lg"
                  loading={isSubmitting || mutation.isPending}
                >
                  <FiSave /> Enregistrer les modifications
                </Button>
              </Flex>
            )}
          </Stack>
        </Flex>
      </form>
    </Container>
  );
};

const ProfileSkeleton = () => (
  <Container maxW="container.xl" py={8}>
    <Box
      h="200px"
      bg="bg.subtle"
      borderRadius="2xl"
      mb={16}
      position="relative"
    >
      <Box position="absolute" bottom="-50px" left="40px">
        <SkeletonCircle size="32" />
      </Box>
    </Box>
    <Flex gap={8}>
      <Stack flex="1">
        <SkeletonText noOfLines={5} gap={4} />
      </Stack>
      <Stack flex="2">
        <SkeletonText noOfLines={8} gap={4} />
      </Stack>
    </Flex>
  </Container>
);

export default CompanyProfile;
