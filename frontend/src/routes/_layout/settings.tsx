import { Box, Container, Flex, Heading, Tabs, Text, useBreakpointValue } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"
import { FiLock, FiMonitor, FiUser, FiUserX } from "react-icons/fi"

import Appearance from "@/components/UserSettings/Appearance"
import ChangePassword from "@/components/UserSettings/ChangePassword"
import DeleteAccount from "@/components/UserSettings/DeleteAccount"
import UserInformation from "@/components/UserSettings/UserInformation"

export const Route = createFileRoute("/_layout/settings")({
  component: UserSettings,
})

const tabsConfig = [
  { value: "profile", title: "Profil", icon: FiUser, component: UserInformation },
  { value: "password", title: "Sécurité", icon: FiLock, component: ChangePassword },
  { value: "appearance", title: "Apparence", icon: FiMonitor, component: Appearance },
  { value: "danger", title: "Zone Danger", icon: FiUserX, component: DeleteAccount },
]

function UserSettings() {
  const isMobile = useBreakpointValue({ base: true, md: false })

  return (
    <Container maxW="container.lg" py={8}>
      <Heading size="2xl" mb={2}>Paramètres</Heading>
      <Text color="fg.muted" mb={8}>Gérez vos informations personnelles et préférences.</Text>

      <Tabs.Root 
        defaultValue="profile" 
        orientation={isMobile ? "horizontal" : "vertical"}
        variant="line"
      >
        <Flex direction={{ base: "column", md: "row" }} gap={8} w="full">
            {/* Sidebar Navigation */}
            <Tabs.List 
                w={{ base: "full", md: "250px" }} 
                borderRightWidth={{ base: 0, md: "1px" }} 
                borderBottomWidth={{ base: "1px", md: 0 }}
                borderColor="border.subtle"
                flexShrink={0}
            >
            {tabsConfig.map((tab) => (
                <Tabs.Trigger 
                    key={tab.value} 
                    value={tab.value} 
                    justifyContent="flex-start" 
                    py={3} 
                    px={4}
                    gap={3}
                    _selected={{ color: "brand.600", borderColor: "brand.600", bg: "brand.50", _dark: { bg: "whiteAlpha.100" } }}
                >
                    <tab.icon /> {tab.title}
                </Tabs.Trigger>
            ))}
            </Tabs.List>

            {/* Content Area */}
            <Box flex="1" minW="0">
                {tabsConfig.map((tab) => (
                    <Tabs.Content key={tab.value} value={tab.value} p={0} mt={{ base: 4, md: 0 }}>
                        <tab.component />
                    </Tabs.Content>
                ))}
            </Box>
        </Flex>
      </Tabs.Root>
    </Container>
  )
}