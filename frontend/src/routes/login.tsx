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
} from "@chakra-ui/react";
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router";
import { type FormEvent, useState } from "react";
import { FiEye, FiEyeOff, FiLogIn } from "react-icons/fi";

import useAuth, { isLoggedIn } from "@/hooks/useAuth";

const LoginPage = () => {
  const { loginMutation } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({ username: "", password: "" });
  const [errors, setErrors] = useState({ username: "", password: "" });

  const showToast = (
    options: {
      title: string;
      description?: string;
      status?: string;
      duration?: number;
      isClosable?: boolean;
    } & Record<string, unknown>
  ) => {
    const message = [options.title, options.description]
      .filter(Boolean)
      .join("\n");
    if (typeof window !== "undefined") {
      window.alert(message || options.title);
    } else {
      console.log("Toast: ", message || options.title);
    }
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (loginMutation.isPending) return;

    // Frontend validation
    const newErrors = { username: "", password: "" };

    if (!formData.username.trim()) {
      newErrors.username = "Veuillez saisir votre email";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.username)) {
      newErrors.username = "L'email doit être valide";
    }

    if (!formData.password) {
      newErrors.password = "Veuillez saisir votre mot de passe";
    } else if (formData.password.length < 8) {
      newErrors.password =
        "Le mot de passe doit contenir au moins 8 caractères";
    }

    if (newErrors.username || newErrors.password) {
      setErrors(newErrors);
      return;
    }

    setErrors({ username: "", password: "" });

    loginMutation.mutate(formData, {
      onSuccess: () => {
        showToast({
          title: "Connexion réussie!",
          description: "Bienvenue sur la plateforme",
          status: "success",
          duration: 3000,
          isClosable: true,
        });
      },
      onError: () => {
        showToast({
          title: "Identifiants incorrects",
          description: "Veuillez vérifier votre email et mot de passe",
          status: "error",
          duration: 5000,
          isClosable: true,
        });
      },
    });
  };

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
            bgGradient="linear(to-r, teal.400, blue.500)"
            bgClip="text"
          >
            Plateforme Logistique
          </Heading>
          <Text color="gray.600" fontSize="lg">
            Connectez-vous à votre compte
          </Text>
        </Box>

        <CardRoot variant="elevated" borderRadius="xl" boxShadow="xl">
          <CardBody p={8}>
            <form onSubmit={handleSubmit}>
              <Stack gap={5}>
                <Box>
                  <chakra.label
                    htmlFor="email"
                    fontSize="sm"
                    fontWeight="semibold"
                    mb={2}
                  >
                    Email
                  </chakra.label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.username}
                    onChange={(event) =>
                      setFormData((prev) => ({
                        ...prev,
                        username: event.target.value,
                      }))
                    }
                    placeholder="exemple@email.com"
                    size="lg"
                    autoComplete="email"
                    _invalid={errors.username ? {} : undefined}
                  />
                  {errors.username && (
                    <Text color="red.500" fontSize="sm" mt={1}>
                      {errors.username}
                    </Text>
                  )}
                </Box>

                <Box>
                  <chakra.label
                    htmlFor="password"
                    fontSize="sm"
                    fontWeight="semibold"
                    mb={2}
                  >
                    Mot de passe
                  </chakra.label>
                  <Flex align="center" gap={2}>
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      value={formData.password}
                      onChange={(event) =>
                        setFormData((prev) => ({
                          ...prev,
                          password: event.target.value,
                        }))
                      }
                      placeholder="••••••••"
                      autoComplete="current-password"
                      flex={1}
                      _invalid={errors.password ? {} : undefined}
                    />
                    {errors.password && (
                      <Text color="red.500" fontSize="sm" mt={1}>
                        {errors.password}
                      </Text>
                    )}
                    <IconButton
                      aria-label={showPassword ? "Masquer" : "Afficher"}
                      variant="ghost"
                      onClick={() => setShowPassword((value) => !value)}
                      size="sm"
                    >
                      {showPassword ? <FiEyeOff /> : <FiEye />}
                    </IconButton>
                  </Flex>
                </Box>

                <Flex justifyContent="flex-end">
                  <RouterLink
                    to="/reset-password"
                    style={{ color: "#0ea5e9", fontSize: "0.875rem" }}
                  >
                    Mot de passe oublié?
                  </RouterLink>
                </Flex>

                <Button
                  type="submit"
                  colorScheme="teal"
                  size="lg"
                  width="full"
                  loading={loginMutation.isPending}
                >
                  <FiLogIn style={{ marginRight: "8px" }} />
                  {loginMutation.isPending ? "Connexion..." : "Se connecter"}
                </Button>
              </Stack>
            </form>
          </CardBody>
        </CardRoot>

        <Text textAlign="center" mt={6} color="gray.600">
          Pas encore de compte?{" "}
          <RouterLink
            to="/signup"
            style={{ color: "#0ea5e9", fontWeight: 600 }}
          >
            Créer un compte
          </RouterLink>
        </Text>

        <Box mt={8} p={4} bg="blue.50" borderRadius="lg">
          <Text fontSize="sm" fontWeight="bold" color="blue.800" mb={2}>
            🔐 Compte de démonstration
          </Text>
          <Text fontSize="sm" color="blue.700">
            Email: <strong>user0@example.dz</strong>
          </Text>
          <Text fontSize="sm" color="blue.700">
            Mot de passe: <strong>password123</strong>
          </Text>
        </Box>
      </Container>
    </Box>
  );
};

export const Route = createFileRoute("/login")({
  component: LoginPage,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({ to: "/" });
    }
  },
});
export default LoginPage;
