import {
  Box,
  Button,
  CardBody,
  CardRoot,
  Container,
  chakra,
  Flex,
  Heading,
  IconButton,
  Input,
  Stack,
  Text,
} from "@chakra-ui/react"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { useState } from "react"
import { FiEye, FiEyeOff, FiUserPlus } from "react-icons/fi"

import useAuth, { isLoggedIn } from "@/hooks/useAuth"

const initialState = {
  email: "",
  full_name: "",
  password: "",
  confirmPassword: "",
}

const SignupPage = () => {
  const { signUpMutation } = useAuth()
  const [showPassword, setShowPassword] = useState(false)
  const [formData, setFormData] = useState(initialState)
  const [passwordStrength, setPasswordStrength] = useState(0)
  const [errors, setErrors] = useState({
    email: "",
    full_name: "",
    password: "",
    confirmPassword: "",
  })

  const showToast = (options: {
    title: string
    description?: string
    status?: string
    duration?: number
    isClosable?: boolean
  }) => {
    const message = [options.title, options.description]
      .filter(Boolean)
      .join("\n")
    if (typeof window !== "undefined") {
      window.alert(message || options.title)
    } else {
      console.log("Toast: ", message || options.title)
    }
  }

  const calculatePasswordStrength = (password: string) => {
    let strength = 0
    if (password.length >= 8) strength += 25
    if (/[a-z]/.test(password)) strength += 25
    if (/[A-Z]/.test(password)) strength += 25
    if (/[0-9]/.test(password)) strength += 25
    return strength
  }

  const handlePasswordChange = (password: string) => {
    setErrors((prev) => ({ ...prev, password: "", confirmPassword: "" }))
    setFormData((prev) => ({ ...prev, password }))
    setPasswordStrength(calculatePasswordStrength(password))
  }

  const getPasswordColor = () => {
    if (passwordStrength < 50) return "red"
    if (passwordStrength < 75) return "orange"
    return "green"
  }

  const validateForm = (): boolean => {
    const newErrors = {
      email: "",
      full_name: "",
      password: "",
      confirmPassword: "",
    }

    // Full name validation
    if (!formData.full_name.trim()) {
      newErrors.full_name = "Veuillez saisir votre nom complet"
    } else if (formData.full_name.trim().length < 3) {
      newErrors.full_name = "Le nom doit contenir au moins 3 caractères"
    } else if (!/^[a-zA-ZÀ-ÿ\s'-]+$/.test(formData.full_name)) {
      newErrors.full_name = "Le nom ne doit contenir que des lettres"
    }

    // Email validation
    if (!formData.email.trim()) {
      newErrors.email = "Veuillez saisir votre email"
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "L'email doit être valide"
    }

    // Password validation
    if (!formData.password) {
      newErrors.password = "Veuillez saisir un mot de passe"
    } else if (formData.password.length < 8) {
      newErrors.password = "Le mot de passe doit contenir au moins 8 caractères"
    } else if (!/[a-z]/.test(formData.password)) {
      newErrors.password =
        "Le mot de passe doit contenir au moins une minuscule"
    } else if (!/[A-Z]/.test(formData.password)) {
      newErrors.password =
        "Le mot de passe doit contenir au moins une majuscule"
    } else if (!/[0-9]/.test(formData.password)) {
      newErrors.password = "Le mot de passe doit contenir au moins un chiffre"
    }

    // Confirm password validation
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = "Veuillez confirmer votre mot de passe"
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = "Les mots de passe ne correspondent pas"
    }

    setErrors(newErrors)
    return !Object.values(newErrors).some((error) => error !== "")
  }

  const handleSubmit = () => {
    if (signUpMutation.isPending) return

    if (!validateForm()) {
      return
    }

    signUpMutation.mutate(
      {
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name,
      },
      {
        onSuccess: () => {
          showToast({
            title: "Compte créé avec succès!",
            description: "Vous pouvez maintenant vous connecter",
            status: "success",
            duration: 5000,
            isClosable: true,
          })
          setFormData(initialState)
          setPasswordStrength(0)
          setErrors({
            email: "",
            full_name: "",
            password: "",
            confirmPassword: "",
          })
        },
        onError: (error) => {
          const detail = (error?.body as any)?.detail
          let description = "Une erreur est survenue"

          if (Array.isArray(detail)) {
            description = detail.map((item: any) => item.msg).join(", ")
          } else if (typeof detail === "string") {
            if (
              detail.toLowerCase().includes("email") &&
              detail.toLowerCase().includes("exist")
            ) {
              description =
                "Cet email est déjà utilisé. Veuillez en choisir un autre."
            } else {
              description = detail
            }
          }

          showToast({
            title: "Erreur d'inscription",
            description,
            status: "error",
            duration: 5000,
            isClosable: true,
          })
        },
      },
    )
  }

  return (
    <Box
      minH="100vh"
      bg="gray.50"
      display="flex"
      alignItems="center"
      justifyContent="center"
      py={12}
      px={4}
    >
      <Container maxW="md">
        <Box textAlign="center" mb={8}>
          <Heading
            size="2xl"
            mb={2}
            bgGradient="linear(to-r, purple.400, pink.500)"
            bgClip="text"
          >
            🚛 Plateforme Logistique
          </Heading>
          <Text color="gray.600" fontSize="lg">
            Créez votre compte
          </Text>
        </Box>

        <CardRoot variant="elevated" borderRadius="xl" boxShadow="xl">
          <CardBody p={8}>
            <Stack gap={5}>
              <Box>
                <chakra.label
                  htmlFor="full-name"
                  mb={2}
                  fontSize="sm"
                  fontWeight="semibold"
                >
                  Nom complet
                </chakra.label>
                <Input
                  id="full-name"
                  type="text"
                  value={formData.full_name}
                  onChange={(event) => {
                    setErrors((prev) => ({ ...prev, full_name: "" }))
                    setFormData((prev) => ({
                      ...prev,
                      full_name: event.target.value,
                    }))
                  }}
                  placeholder="Ahmed Benali"
                  size="lg"
                  autoComplete="name"
                  _invalid={errors.full_name ? {} : undefined}
                />
                {errors.full_name && (
                  <Text color="red.500" fontSize="sm" mt={1}>
                    {errors.full_name}
                  </Text>
                )}
              </Box>

              <Box>
                <chakra.label
                  htmlFor="email"
                  mb={2}
                  fontSize="sm"
                  fontWeight="semibold"
                >
                  Email
                </chakra.label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(event) => {
                    setErrors((prev) => ({ ...prev, email: "" }))
                    setFormData((prev) => ({
                      ...prev,
                      email: event.target.value,
                    }))
                  }}
                  placeholder="exemple@email.com"
                  size="lg"
                  autoComplete="email"
                  _invalid={errors.email ? {} : undefined}
                />
                {errors.email && (
                  <Text color="red.500" fontSize="sm" mt={1}>
                    {errors.email}
                  </Text>
                )}
              </Box>

              <Box>
                <chakra.label
                  htmlFor="password"
                  mb={2}
                  fontSize="sm"
                  fontWeight="semibold"
                >
                  Mot de passe
                </chakra.label>
                <Flex align="center" gap={2}>
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={formData.password}
                    onChange={(event) =>
                      handlePasswordChange(event.target.value)
                    }
                    placeholder="••••••••"
                    autoComplete="new-password"
                    flex={1}
                    _invalid={errors.password ? {} : undefined}
                  />
                  <IconButton
                    aria-label={showPassword ? "Masquer" : "Afficher"}
                    variant="ghost"
                    onClick={() => setShowPassword((value) => !value)}
                    size="sm"
                  >
                    {showPassword ? <FiEyeOff /> : <FiEye />}
                  </IconButton>
                </Flex>

                {errors.password && (
                  <Text color="red.500" fontSize="sm" mt={1}>
                    {errors.password}
                  </Text>
                )}

                {formData.password && !errors.password && (
                  <Box mt={2}>
                    <Flex justifyContent="space-between" mb={1}>
                      <Text fontSize="xs" color="gray.600">
                        Force du mot de passe
                      </Text>
                      <Text fontSize="xs" color={`${getPasswordColor()}.600`}>
                        {passwordStrength < 50 && "Faible"}
                        {passwordStrength >= 50 &&
                          passwordStrength < 75 &&
                          "Moyen"}
                        {passwordStrength >= 75 && "Fort"}
                      </Text>
                    </Flex>
                    <Box
                      height="6px"
                      bg="gray.200"
                      borderRadius="full"
                      overflow="hidden"
                    >
                      <Box
                        height="100%"
                        bg={`${getPasswordColor()}.400`}
                        width={`${passwordStrength}%`}
                        transition="width 0.2s ease"
                      />
                    </Box>
                  </Box>
                )}
              </Box>

              <Box>
                <chakra.label
                  htmlFor="confirm-password"
                  mb={2}
                  fontSize="sm"
                  fontWeight="semibold"
                >
                  Confirmer le mot de passe
                </chakra.label>
                <Input
                  id="confirm-password"
                  type="password"
                  value={formData.confirmPassword}
                  onChange={(event) => {
                    setErrors((prev) => ({ ...prev, confirmPassword: "" }))
                    setFormData((prev) => ({
                      ...prev,
                      confirmPassword: event.target.value,
                    }))
                  }}
                  placeholder="••••••••"
                  autoComplete="new-password"
                  size="lg"
                  _invalid={errors.confirmPassword ? {} : undefined}
                />
                {errors.confirmPassword && (
                  <Text color="red.500" fontSize="sm" mt={1}>
                    {errors.confirmPassword}
                  </Text>
                )}
              </Box>

              <Box bg="gray.50" p={3} borderRadius="md">
                <Text fontSize="xs" color="gray.600">
                  ✓ Au moins 8 caractères
                  <br />✓ Majuscules et minuscules
                  <br />✓ Au moins un chiffre
                </Text>
              </Box>

              <Button
                onClick={handleSubmit}
                colorScheme="purple"
                size="lg"
                width="full"
                disabled={
                  signUpMutation.isPending ||
                  !formData.email ||
                  !formData.password ||
                  !formData.full_name
                }
                loading={signUpMutation.isPending}
                loadingText="Création du compte..."
              >
                <FiUserPlus style={{ marginRight: "8px" }} />
                Créer mon compte
              </Button>
            </Stack>
          </CardBody>
        </CardRoot>

        <Text textAlign="center" mt={6} color="gray.600">
          Déjà un compte?{" "}
          <RouterLink to="/login" style={{ color: "#805ad5", fontWeight: 600 }}>
            Se connecter
          </RouterLink>
        </Text>

        <Box mt={8} p={4} bg="purple.50" borderRadius="lg">
          <Text fontSize="sm" color="purple.700">
            📝 Après l'inscription, vous devrez créer votre profil d'entreprise
            pour accéder à toutes les fonctionnalités.
          </Text>
        </Box>
      </Container>
    </Box>
  )
}

export const Route = createFileRoute("/signup")({
  component: SignupPage,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
})

export default SignupPage
