import { Flex, Spinner, Center } from "@chakra-ui/react"
import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"

import Navbar from "@/components/Common/Navbar"
import Sidebar from "@/components/Common/Sidebar"
import CompanyOnboardingModal from "@/components/Company/CompanyOnboardingModal"
import { isLoggedIn } from "@/hooks/useAuth"
import { useCompany } from "@/hooks/useCompany"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout")({
  component: Layout,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({
        to: "/login",
      })
    }
  },
})

function Layout() {
  const { user } = useAuth()
  const { company, isLoading: isLoadingCompany } = useCompany()

  // Wait for user to be loaded first
  if (!user) {
    return (
      <Center h="100vh" bg="bg.canvas">
        <Spinner size="xl" color="brand.500" />
      </Center>
    )
  }

  // Check if we need to show the Onboarding Modal
  // Condition: Company query finished, and result is null
  const showOnboarding = !isLoadingCompany && !company

  return (
    <Flex direction="column" h="100vh" bg="bg.canvas">
      <Navbar />
      <Flex flex="1" overflow="hidden">
        <Sidebar />
        <Flex flex="1" direction="column" p={4} overflowY="auto" position="relative">
          {/* 
             Only render the main content (Dashboard, etc.) if we HAVE a company.
             Otherwise, the child components (like Dashboard) will fire API calls 
             that 404 and crash the app.
          */}
          {company ? <Outlet /> : null}
        </Flex>
      </Flex>

      {/* This modal handles the "Create Company" flow if missing */}
      <CompanyOnboardingModal isOpen={showOnboarding} />
    </Flex>
  )
}

export default Layout