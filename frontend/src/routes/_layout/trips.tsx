import { createFileRoute } from "@tanstack/react-router"

import TripManagementPage from "../../components/Trips/TripManagement"

export const Route = createFileRoute("/_layout/trips")({
  component: TripManagementPage,
})
