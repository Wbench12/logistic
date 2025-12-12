import { createFileRoute } from "@tanstack/react-router"

import SidebarItems from "@/components/Common/SidebarItems"

export const Route = createFileRoute("/_layout/items")({
  component: SidebarItems,
})
