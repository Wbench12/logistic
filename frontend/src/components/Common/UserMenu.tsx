import { Avatar, Box, Flex, HStack, Text } from "@chakra-ui/react"
import { Link } from "@tanstack/react-router"
import { FiLogOut, FiSettings, FiUser } from "react-icons/fi"

import useAuth from "@/hooks/useAuth"
import {
  MenuContent,
  MenuItem,
  MenuRoot,
  MenuTrigger,
} from "@/components/ui/menu"

const UserMenu = () => {
  const { user, logout } = useAuth()

  return (
    <MenuRoot positioning={{ placement: "bottom-end" }}>
      <MenuTrigger asChild cursor="pointer">
        <HStack 
            gap={3} 
            p={1.5} 
            pr={3}
            borderRadius="full" 
            transition="background 0.2s" 
            _hover={{ bg: "gray.50" }}
        >
          <Avatar.Root size="sm" colorPalette="brand" variant="solid">
            <Avatar.Fallback name={user?.full_name || "User"} />
          </Avatar.Root>
          {/* Hide name on mobile to save space, show on desktop */}
          <Box display={{ base: "none", md: "block" }}>
             <Text fontSize="sm" fontWeight="medium" color="gray.700" lineHeight="1">
                {user?.full_name?.split(" ")[0]}
             </Text>
          </Box>
        </HStack>
      </MenuTrigger>

      <MenuContent minW="200px" borderRadius="xl" boxShadow="lg">
        <Box px={3} py={2} borderBottomWidth="1px" borderColor="gray.100">
           <Text fontSize="sm" fontWeight="bold" color="gray.800">Compte</Text>
           <Text fontSize="xs" color="gray.500" truncate>{user?.email}</Text>
        </Box>

        <Link to="/settings">
          <MenuItem value="profile" gap={2} p={2.5}>
            <FiUser /> Mon Profil
          </MenuItem>
        </Link>
        <Link to="/settings">
           <MenuItem value="settings" gap={2} p={2.5}>
             <FiSettings /> Paramètres
           </MenuItem>
        </Link>
        
        <MenuItem 
            value="logout" 
            gap={2} 
            p={2.5} 
            color="red.600" 
            _hover={{ bg: "red.50" }}
            onClick={logout}
        >
          <FiLogOut /> Se déconnecter
        </MenuItem>
      </MenuContent>
    </MenuRoot>
  )
}

export default UserMenu