import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { createRouter, RouterProvider } from "@tanstack/react-router";
import { StrictMode } from "react";
import ReactDOM from "react-dom/client";
import { ApiError, OpenAPI } from "./client";
import { CustomProvider } from "./components/ui/provider";
import { routeTree } from "./routeTree.gen";
import { triggerServerDown } from "./utils"; // Import the trigger

const rawApiBase = (import.meta.env.VITE_API_URL || "").trim();
const normalizedApiBase = rawApiBase.replace(/\/+$/, "");

// In dev, prefer Vite proxy (BASE="") unless VITE_API_URL is explicitly set.
// In prod, use VITE_API_URL when provided, otherwise same-origin.
OpenAPI.BASE = normalizedApiBase || "";

OpenAPI.TOKEN = async () => {
  return localStorage.getItem("access_token") || "";
};

const handleApiError = (error: Error) => {
  // 1. Auth Errors -> Login
  if (error instanceof ApiError && [401, 403].includes(error.status)) {
    localStorage.removeItem("access_token");
    window.location.href = "/login";
    return;
  }

  // 2. Server/Network Errors -> Show ServerDown Screen
  // Status 0 = Network Error (Server down/Unreachable)
  // Status 502/503 = Bad Gateway/Service Unavailable
  if (
    (error instanceof ApiError && [502, 503].includes(error.status)) ||
    error.message === "Network Error" ||
    // @ts-ignore
    error.status === 0
  ) {
    triggerServerDown();
  }
};

const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: handleApiError,
  }),
  mutationCache: new MutationCache({
    onError: handleApiError,
  }),
  defaultOptions: {
    queries: {
      retry: 1, // Don't retry too many times if server is dead
    },
  },
});

const router = createRouter({ routeTree });
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <CustomProvider>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </CustomProvider>
  </StrictMode>
);
