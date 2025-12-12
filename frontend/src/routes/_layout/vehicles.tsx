import { createFileRoute } from "@tanstack/react-router"

import VehicleManagementPage from "@/components/Vehicles/VehicleManagement"

export const Route = createFileRoute("/_layout/vehicles")({
  component: VehicleManagementPage,
})
