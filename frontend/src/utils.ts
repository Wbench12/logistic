import type { ApiError } from "./client"
import useCustomToast from "./hooks/useCustomToast"

/**
 * Extract user-friendly error message from API error
 */
export const getErrorMessage = (error: unknown): string => {
  if (!error) return "Une erreur inattendue s'est produite"

  const apiError = error as ApiError
  const body = apiError?.body as any

  if (body?.detail) {
    return typeof body.detail === "string"
      ? body.detail
      : JSON.stringify(body.detail)
  }

  if (apiError?.message) {
    return apiError.message
  }

  return "Une erreur s'est produite lors de la requête"
}

export const getValidationErrors = (error: unknown): string[] | null => {
  const apiError = error as ApiError
  const body = apiError?.body as any

  if (body?.errors && Array.isArray(body.errors)) {
    return body.errors
  }

  return null
}

export const emailPattern = {
  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
  message: "Invalid email address",
}

export const namePattern = {
  value: /^[A-Za-z\s\u00C0-\u017F]{1,30}$/,
  message: "Invalid name",
}

export const passwordRules = (isRequired = true) => {
  const rules: any = {
    minLength: {
      value: 8,
      message: "Password must be at least 8 characters",
    },
  }

  if (isRequired) {
    rules.required = "Password is required"
  }

  return rules
}

export const confirmPasswordRules = (
  getValues: () => any,
  isRequired = true,
) => {
  const rules: any = {
    validate: (value: string) => {
      const password = getValues().password || getValues().new_password
      return value === password ? true : "The passwords do not match"
    },
  }

  if (isRequired) {
    rules.required = "Password confirmation is required"
  }

  return rules
}

export const handleError = (err: ApiError) => {
  const { showErrorToast } = useCustomToast()
  const errDetail = (err.body as any)?.detail
  let errorMessage = errDetail || "Something went wrong."
  if (Array.isArray(errDetail) && errDetail.length > 0) {
    errorMessage = errDetail[0].msg
  }
  showErrorToast(errorMessage)
}

// --- Server Status Event System ---
export const SERVER_DOWN_EVENT = "server-down"

export const triggerServerDown = () => {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(SERVER_DOWN_EVENT))
  }
}

// --- GEOCODING SERVICE ---
const GEO_API_KEY = "693f315da7a7e912239559anub9eec6"

export interface GeoResult {
  lat: number
  lng: number
  display_name: string
}

export const GeocodingService = {
  // 1. Forward Geocoding: Address string -> Coordinates
  searchAddress: async (query: string): Promise<GeoResult | null> => {
    try {
      await new Promise((resolve) => setTimeout(resolve, 500)) // Throttle

      const url = `https://geocode.maps.co/search?q=${encodeURIComponent(
        query,
      )}&api_key=${GEO_API_KEY}`
      const res = await fetch(url)

      if (!res.ok) return null

      const data = await res.json()

      if (data && data.length > 0) {
        return {
          lat: parseFloat(data[0].lat),
          lng: parseFloat(data[0].lon),
          display_name: data[0].display_name,
        }
      }
      return null
    } catch (error) {
      console.error("Geocoding network error:", error)
      return null
    }
  },

  // 2. Reverse Geocoding: Coordinates -> Address string
  reverseGeocode: async (lat: number, lng: number): Promise<string | null> => {
    try {
      await new Promise((resolve) => setTimeout(resolve, 500)) // Throttle

      const url = `https://geocode.maps.co/reverse?lat=${lat}&lon=${lng}&api_key=${GEO_API_KEY}`
      const res = await fetch(url)

      if (!res.ok) return null

      const data = await res.json()

      return data.display_name || "Adresse inconnue"
    } catch (error) {
      console.error("Reverse geocoding network error:", error)
      return null
    }
  },
}