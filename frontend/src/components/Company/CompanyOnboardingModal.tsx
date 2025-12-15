import {
  Box,
  Button,
  DialogBackdrop,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogRoot,
  DialogTitle,
  Heading,
  Input,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { FiBriefcase, FiCheck, FiShield } from "react-icons/fi";

import { type ApiError, type CompanyCreate, CompaniesService } from "@/client";
import { Field } from "@/components/ui/field";
import { Toaster, toaster } from "@/components/ui/toaster";
import { handleError } from "@/utils";

interface OnboardingProps {
  isOpen: boolean;
}

// Config options
const COMPANY_TYPE_OPTIONS = [
  { value: "production", label: "Production" },
  { value: "negoce", label: "Négoce" },
  { value: "service", label: "Services" },
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

const CompanyOnboardingModal = ({ isOpen }: OnboardingProps) => {
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CompanyCreate>({
    defaultValues: {
      company_type: "production",
      partner_type: "entreprise",
      activity_sector: "agroalimentaire",
    },
  });

  const mutation = useMutation({
    mutationFn: (data: CompanyCreate) =>
      CompaniesService.createCompany({ requestBody: data }),
    onSuccess: (data) => {
      toaster.success({
        title: "Bienvenue !",
        description: `${data.company_name} a été enregistrée avec succès.`,
      });
      // Immediately update cache so the modal closes and app unlocks
      queryClient.setQueryData(["companyProfile"], data);
      queryClient.invalidateQueries({ queryKey: ["companyProfile"] });
    },
    onError: (err: ApiError) => handleError(err),
  });

  const onSubmit = (data: CompanyCreate) => {
    mutation.mutate(data);
  };

  return (
    <DialogRoot
      open={isOpen}
      // Prevent closing by clicking outside or pressing Escape
      closeOnEscape={false}
      closeOnInteractOutside={false}
      size="lg"
    >
      <DialogBackdrop bg="blackAlpha.800" backdropFilter="blur(5px)" />
      <DialogContent borderRadius="xl" boxShadow="2xl">
        <DialogHeader
          borderBottomWidth="1px"
          borderColor="border.subtle"
          pb={4}
        >
          <VStack align="start" gap={1}>
            <Heading
              size="lg"
              color="brand.600"
              display="flex"
              alignItems="center"
              gap={2}
            >
              <FiBriefcase /> Configuration Requise
            </Heading>
            <DialogTitle srOnly>Enregistrement Entreprise</DialogTitle>
            <Text color="fg.muted" fontSize="sm">
              Pour accéder à la plateforme, veuillez enregistrer votre profil
              d'entreprise.
            </Text>
          </VStack>
        </DialogHeader>

        <DialogBody py={6}>
          <form id="onboarding-form" onSubmit={handleSubmit(onSubmit)}>
            <Stack gap={5}>
              {/* Identity */}
              <Field
                label="Nom de l'entreprise"
                required
                invalid={!!errors.company_name}
                errorText={errors.company_name?.message}
              >
                <Input
                  {...register("company_name", { required: "Requis" })}
                  placeholder="Ex: Globex Logistics"
                />
              </Field>

              <SimpleGrid columns={2} gap={4}>
                <Field label="Type" required>
                  <select
                    {...register("company_type")}
                    style={{
                      width: "100%",
                      padding: "10px",
                      borderRadius: "6px",
                      border: "1px solid #E2E8F0",
                    }}
                  >
                    {COMPANY_TYPE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Secteur" required>
                  <select
                    {...register("activity_sector")}
                    style={{
                      width: "100%",
                      padding: "10px",
                      borderRadius: "6px",
                      border: "1px solid #E2E8F0",
                    }}
                  >
                    {ACTIVITY_SECTOR_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </Field>
              </SimpleGrid>

              {/* Legal Info */}
              <Box
                p={4}
                bg="bg.subtle"
                borderRadius="md"
                borderWidth="1px"
                borderColor="border.subtle"
              >
                <Text
                  fontWeight="bold"
                  mb={3}
                  display="flex"
                  alignItems="center"
                  gap={2}
                  fontSize="sm"
                >
                  <FiShield /> Informations Légales
                </Text>
                <SimpleGrid columns={2} gap={4} mb={4}>
                  <Field
                    label="NIS"
                    required
                    invalid={!!errors.nis}
                    errorText={errors.nis?.message}
                  >
                    <Input
                      {...register("nis", {
                        required: "Requis",
                        minLength: { value: 5, message: "Min 5 chiffres" },
                      })}
                      placeholder="12345..."
                    />
                  </Field>
                  <Field
                    label="NIF"
                    required
                    invalid={!!errors.nif}
                    errorText={errors.nif?.message}
                  >
                    <Input
                      {...register("nif", {
                        required: "Requis",
                        minLength: { value: 5, message: "Min 5 chiffres" },
                      })}
                      placeholder="98765..."
                    />
                  </Field>
                </SimpleGrid>
                <Field
                  label="Adresse du Siège"
                  required
                  invalid={!!errors.headquarters_address}
                  errorText={errors.headquarters_address?.message}
                >
                  <Textarea
                    {...register("headquarters_address", {
                      required: "Requis",
                    })}
                    rows={2}
                    bg="bg.panel"
                  />
                </Field>
              </Box>

              {/* Contact */}
              <SimpleGrid columns={2} gap={4}>
                <Field
                  label="Représentant Légal"
                  required
                  invalid={!!errors.legal_representative_name}
                >
                  <Input
                    {...register("legal_representative_name", {
                      required: "Requis",
                    })}
                  />
                </Field>
                <Field
                  label="Téléphone"
                  required
                  invalid={!!errors.legal_representative_contact}
                >
                  <Input
                    {...register("legal_representative_contact", {
                      required: "Requis",
                    })}
                  />
                </Field>
              </SimpleGrid>

              {/* Hidden Defaults */}
              <input
                type="hidden"
                {...register("partner_type")}
                value="entreprise"
              />

              <Button
                type="submit"
                colorPalette="brand"
                size="lg"
                w="full"
                mt={2}
                loading={mutation.isPending || isSubmitting}
              >
                <FiCheck /> Créer et Accéder au Dashboard
              </Button>
            </Stack>
          </form>
        </DialogBody>
      </DialogContent>
      <Toaster />
    </DialogRoot>
  );
};

export default CompanyOnboardingModal;
