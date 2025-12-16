import {
  Box,
  Button,
  Container,
  Heading,
  Icon,
  Text,
  VStack,
} from "@chakra-ui/react"
import { FiRefreshCw, FiWifiOff } from "react-icons/fi"

interface ServerDownProps {
  onRetry: () => void
}

const ServerDown = ({ onRetry }: ServerDownProps) => {
  return (
    <Box
      position="fixed"
      top={0}
      left={0}
      w="100vw"
      h="100vh"
      bg="bg.canvas"
      zIndex={9999}
      display="flex"
      alignItems="center"
      justifyContent="center"
    >
      <Container maxW="md" centerContent>
        <VStack gap={6} textAlign="center">
          <Box
            p={6}
            bg="red.50"
            _dark={{ bg: "red.900/20" }}
            borderRadius="full"
            color="red.500"
          >
            <Icon as={FiWifiOff} boxSize={12} />
          </Box>

          <VStack gap={2}>
            <Heading size="xl" color="fg.default">
              Serveur Inaccessible
            </Heading>
            <Text color="fg.muted" fontSize="lg">
              Nous n'arrivons pas à joindre le serveur. Il est peut-être en maintenance ou votre connexion est instable.
            </Text>
          </VStack>

          <Button
            size="lg"
            colorPalette="brand"
            onClick={onRetry}
            mt={4}
          >
            <FiRefreshCw /> Réessayer la connexion
          </Button>
        </VStack>
      </Container>
    </Box>
  )
}

export default ServerDown