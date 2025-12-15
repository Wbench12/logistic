import { CardBody, CardHeader, CardRoot, Heading, Stack, Text } from "@chakra-ui/react"
import { useTheme } from "next-themes"
import { Radio, RadioGroup } from "@/components/ui/radio"

const Appearance = () => {
  const { theme, setTheme } = useTheme()

  return (
    <CardRoot variant="elevated" bg="bg.panel">
      <CardHeader>
        <Heading size="md">Apparence de l'interface</Heading>
        <Text fontSize="sm" color="fg.muted">Choisissez votre thème préféré.</Text>
      </CardHeader>
      <CardBody>
        <RadioGroup
          onValueChange={(e) => setTheme(e.value)}
          value={theme}
          colorPalette="brand"
        >
          <Stack gap={4}>
            <Radio value="light">
                <Stack gap={0}>
                    <Text fontWeight="medium">Clair</Text>
                    <Text fontSize="sm" color="fg.muted">Thème par défaut lumineux</Text>
                </Stack>
            </Radio>
            <Radio value="dark">
                <Stack gap={0}>
                    <Text fontWeight="medium">Sombre</Text>
                    <Text fontSize="sm" color="fg.muted">Meilleur pour les environnements sombres</Text>
                </Stack>
            </Radio>
            <Radio value="system">
                <Stack gap={0}>
                    <Text fontWeight="medium">Système</Text>
                    <Text fontSize="sm" color="fg.muted">S'adapte aux préférences de votre appareil</Text>
                </Stack>
            </Radio>
          </Stack>
        </RadioGroup>
      </CardBody>
    </CardRoot>
  )
}
export default Appearance