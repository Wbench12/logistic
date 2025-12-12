import { createFileRoute } from "@tanstack/react-router"

import CompanyProfile from "@/components/Company/CompanyProfile"

export const Route = createFileRoute("/_layout/company")({
  component: CompanyProfile,
})
