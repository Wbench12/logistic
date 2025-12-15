import { Flex } from "@chakra-ui/react"
import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"

import Navbar from "@/components/Common/Navbar"
import Sidebar from "@/components/Common/Sidebar"
import CompanyOnboardingModal from "@/components/Company/CompanyOnboardingModal"
import { isLoggedIn } from "@/hooks/useAuth"
import { useCompany } from "@/hooks/useCompany"

export const Route = createFileRoute("/_layout")({
  component: Layout,
  // 1. Force Login if no token
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({
        to: "/login",
      })
    }
  },
})

function Layout() {
  const { company, isLoading } = useCompany()

  // 2. Check if user needs to register a company
  // We wait for loading to finish. If finished, and company is null, modal opens.
  const showOnboarding = !isLoading && !company

  return (
    <Flex direction="column" h="100vh" bg="bg.canvas">
      <Navbar />
      <Flex flex="1" overflow="hidden">
        <Sidebar />
        <Flex flex="1" direction="column" p={4} overflowY="auto" position="relative">
          <Outlet />
        </Flex>
      </Flex>

      {/* 
        This Modal sits on top of everything.
        It renders if we fetched data and found NO company profile.
      */}
      <CompanyOnboardingModal isOpen={showOnboarding} />
    </Flex>
  )
}

export default Layout