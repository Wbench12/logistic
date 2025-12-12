import type { ApiError } from "./client"
import useCustomToast from "./hooks/useCustomToast"

/**
 * Extract user-friendly error message from API error
 * Backend now returns formatted errors in { detail, errors } format
 */
export const getErrorMessage = (error: unknown): string => {
  if (!error) return "Une erreur inattendue s'est produite"

  const apiError = error as ApiError
  const body = apiError?.body as any

  // Backend returns formatted message in detail
  if (body?.detail) {
    return typeof body.detail === "string"
      ? body.detail
      : JSON.stringify(body.detail)
  }

  // Fallback to error message
  if (apiError?.message) {
    return apiError.message
  }

  return "Une erreur s'est produite lors de la requête"
}

/**
 * Get array of individual validation errors if available
 */
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
