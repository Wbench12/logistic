import { Box, Flex, Icon, Text } from "@chakra-ui/react"
import { useQueryClient } from "@tanstack/react-query"
import { Link as RouterLink, useLocation } from "@tanstack/react-router"
import {
  FiBriefcase,
  FiGrid,
  FiMap,
  FiSettings,
  FiTruck,
  FiUsers,
} from "react-icons/fi"

import type { UserPublic } from "@/client"

// Navigation Config
const items = [
  { icon: FiGrid, title: "Tableau de Bord", path: "/" },
  { icon: FiTruck, title: "Gestion Flotte", path: "/vehicles" },
  { icon: FiMap, title: "Trajets & Missions", path: "/trips" },
  { icon: FiBriefcase, title: "Entreprise", path: "/company" },
  { icon: FiSettings, title: "Paramètres", path: "/settings" },
]

interface SidebarItemsProps {
  onClose?: () => void
}

const SidebarItems = ({ onClose }: SidebarItemsProps) => {
  const queryClient = useQueryClient()
  const currentUser = queryClient.getQueryData<UserPublic>(["currentUser"])
  const { pathname } = useLocation()

  // Add Admin link if superuser
  const finalItems = currentUser?.is_superuser
    ? [...items, { icon: FiUsers, title: "Administration", path: "/admin" }]
    : items

  return (
    <Box as="ul" listStyleType="none" m={0} p={0} w="full">
      {finalItems.map(({ icon, title, path }) => {
        // Simple active check: Exact match or starts with path (except root)
        const isActive = path === "/" ? pathname === "/" : pathname.startsWith(path)

        return (
          <Box as="li" key={path} px={4} mb={1}>
            <RouterLink to={path} onClick={onClose} style={{ textDecoration: 'none' }}>
              <Flex
                align="center"
                gap={3}
                p={3}
                borderRadius="lg"
                cursor="pointer"
                transition="all 0.2s ease"
                bg={isActive ? "brand.50" : "transparent"}
                color={isActive ? "brand.700" : "gray.600"}
                fontWeight={isActive ? "semibold" : "medium"}
                position="relative"
                _hover={{
                  bg: isActive ? "brand.50" : "gray.50",
                  color: isActive ? "brand.700" : "gray.900",
                }}
              >
                {/* Active Indicator Line (Optional, decorative) */}
                {isActive && (
                  <Box 
                    position="absolute" 
                    left="0" 
                    top="50%" 
                    transform="translateY(-50%)" 
                    h="20px" 
                    w="3px" 
                    bg="brand.600" 
                    borderRightRadius="full"
                  />
                )}

                <Icon as={icon} fontSize="lg" />
                <Text fontSize="sm">{title}</Text>
              </Flex>
            </RouterLink>
          </Box>
        )
      })}
    </Box>
  )
}

export default SidebarItems