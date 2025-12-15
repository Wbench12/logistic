import {
  Avatar,
  Box,
  Flex,
  HStack,
  IconButton,
  Separator,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { FiLogOut, FiMenu, FiX } from "react-icons/fi"

import type { UserPublic } from "@/client"
import useAuth from "@/hooks/useAuth"
import {
  DrawerBackdrop,
  DrawerBody,
  DrawerContent,
  DrawerRoot,
  DrawerTrigger,
} from "@/components/ui/drawer"
import SidebarItems from "./SidebarItems"

const Sidebar = () => {
  const queryClient = useQueryClient()
  const currentUser = queryClient.getQueryData<UserPublic>(["currentUser"])
  const { logout } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  
  // Helper to render the User Footer Profile
  const UserProfileFooter = () => (
    <Box mt="auto" px={4} pb={6}>
      <Separator mb={4} borderColor="border.subtle" />
      <Flex 
        align="center" 
        justify="space-between" 
        p={3} 
        bg="bg.subtle" 
        borderRadius="xl"
        borderWidth="1px"
        borderColor="border.subtle"
      >
        <HStack gap={3} overflow="hidden">
          <Avatar.Root size="sm" colorPalette="brand">
             <Avatar.Fallback name={currentUser?.full_name || "User"} />
          </Avatar.Root>
          <Box minW="0">
            <Text fontSize="sm" fontWeight="semibold" truncate color="fg.default">
              {currentUser?.full_name?.split(" ")[0]}
            </Text>
            <Text fontSize="xs" color="fg.muted" truncate>
              {currentUser?.email}
            </Text>
          </Box>
        </HStack>
        <IconButton
          variant="ghost"
          size="xs"
          color="fg.muted"
          _hover={{ color: "red.500", bg: "red.50", _dark: { bg: "red.900/20" } }}
          onClick={logout}
          aria-label="Logout"
        >
          <FiLogOut />
        </IconButton>
      </Flex>
    </Box>
  )

  // Mobile Drawer
  const MobileSidebar = () => (
    <DrawerRoot placement="start" open={isOpen} onOpenChange={(e) => setIsOpen(e.open)}>
      <DrawerBackdrop />
      <DrawerTrigger asChild>
        <IconButton
          aria-label="Open Menu"
          variant="ghost"
          display={{ base: "flex", md: "none" }}
          position="absolute"
          top={3}
          left={2}
          zIndex="popover"
          color="fg.default"
        >
          <FiMenu />
        </IconButton>
      </DrawerTrigger>
      <DrawerContent bg="bg.panel">
        <DrawerBody p={0} display="flex" flexDirection="column" h="full">
          <Flex justify="end" p={4}>
             <IconButton variant="ghost" size="sm" onClick={() => setIsOpen(false)} color="fg.default">
               <FiX />
             </IconButton>
          </Flex>
          <Box flex="1" py={2}>
            <SidebarItems onClose={() => setIsOpen(false)} />
          </Box>
          <UserProfileFooter />
        </DrawerBody>
      </DrawerContent>
    </DrawerRoot>
  )

  // Desktop Sidebar
  return (
    <>
      <MobileSidebar />
      
      <Flex
        display={{ base: "none", md: "flex" }}
        direction="column"
        w="280px"
        h="calc(100vh - 65px)" // Subtract navbar height roughly
        borderRightWidth="1px"
        borderColor="border.subtle"
        bg="bg.panel"
        position="sticky"
        top="65px"
        overflowY="auto"
      >
        <VStack flex="1" align="stretch" py={6} gap={1}>
          <Text 
            px={6} 
            mb={2} 
            fontSize="xs" 
            fontWeight="bold" 
            textTransform="uppercase" 
            letterSpacing="wider" 
            color="fg.muted"
          >
            Menu Principal
          </Text>
          <SidebarItems />
        </VStack>

        <UserProfileFooter />
      </Flex>
    </>
  )
}

export default Sidebar