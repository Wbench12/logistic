import { Box, Flex, HStack, Image, Skeleton, Text, useBreakpointValue } from "@chakra-ui/react"
import { Link } from "@tanstack/react-router"
import PlatformLogo from "/assets/images/fastapi-logo.svg" 
import UserMenu from "./UserMenu"
import { useCompany } from "@/hooks/useCompany"

function Navbar() {
  const isDesktop = useBreakpointValue({ base: false, lg: true })
  const { company, isLoading } = useCompany()

  return (
    <Flex
      as="nav"
      align="center"
      justify="space-between"
      wrap="wrap"
      w="100%"
      px={8}
      py={3}
      bg="bg.panel" // Changed from white to bg.panel
      borderBottomWidth="1px"
      borderColor="border.subtle"
      position="sticky"
      top={0}
      zIndex="sticky"
    >
      <HStack gap={5}>
        <Link to="/">
          <Image 
            src={PlatformLogo} 
            alt="Platform Logo" 
            h="32px" 
            objectFit="contain" 
            // Invert filter logic for dark mode visibility if logo is black text
            // Assuming FastAPI logo has text that needs to be visible
            _dark={{ filter: "invert(1) grayscale(100%)" }} 
            filter="grayscale(100%)"
            transition="all 0.2s"
            _hover={{ filter: "grayscale(0%)" }}
          />
        </Link>

        {(!isLoading && company?.logo_url) && (
           <Box w="1px" h="24px" bg="border.subtle" transform="skewX(-15deg)" />
        )}

        {!isLoading && company?.logo_url && (
          <Flex align="center" gap={3}>
            <Box 
                bg="white" // Keep logo bg white to ensure visibility
                p={1}
                borderRadius="md" 
                borderWidth="1px" 
                borderColor="border.subtle"
            >
                <Image 
                  src={company.logo_url} 
                  alt="Company Logo" 
                  h="26px" 
                  maxW="120px"
                  objectFit="contain"
                />
            </Box>
            {isDesktop && (
              <Text fontWeight="bold" fontSize="sm" color="fg.default">
                {company.company_name}
              </Text>
            )}
          </Flex>
        )}
        
        {isLoading && <Skeleton height="32px" width="120px" />}
      </HStack>

      <Flex alignItems="center" gap={4}>
        <UserMenu />
      </Flex>
    </Flex>
  )
}

export default Navbar