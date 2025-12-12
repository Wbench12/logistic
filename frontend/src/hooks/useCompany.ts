import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import {
  ApiError,
  CompaniesService,
  type CompanyCreate,
  type CompanyPublic,
  type CompanyUpdate,
} from "@/client"
import useCustomToast from "./useCustomToast"

const COMPANY_QUERY_KEY = ["companyProfile"] as const

const parseApiError = (error: unknown) => {
  if (error instanceof ApiError) {
    const body = error.body as { detail?: string } | undefined
    return body?.detail ?? error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return "Unexpected error"
}

export const useCompany = () => {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const companyQuery = useQuery<CompanyPublic | null>({
    queryKey: COMPANY_QUERY_KEY,
    queryFn: async () => {
      try {
        return await CompaniesService.readCompanyMe()
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          return null
        }
        throw error
      }
    },
    retry: false,
  })

  const createMutation = useMutation({
    mutationFn: async (payload: CompanyCreate) =>
      CompaniesService.createCompany({ requestBody: payload }),
    onSuccess: (data) => {
      queryClient.setQueryData(COMPANY_QUERY_KEY, data)
      showSuccessToast("Profil entreprise créé avec succès.")
    },
    onError: (error) => {
      showErrorToast(parseApiError(error))
    },
  })

  const updateMutation = useMutation({
    mutationFn: async (payload: CompanyUpdate) =>
      CompaniesService.updateCompanyMe({ requestBody: payload }),
    onSuccess: (data) => {
      queryClient.setQueryData(COMPANY_QUERY_KEY, data)
      showSuccessToast("Profil entreprise mis à jour.")
    },
    onError: (error) => {
      showErrorToast(parseApiError(error))
    },
  })

  return {
    company: companyQuery.data,
    isLoading: companyQuery.isPending,
    isError: companyQuery.isError,
    refetchCompany: companyQuery.refetch,
    createCompany: createMutation.mutateAsync,
    updateCompany: updateMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
  }
}

export default useCompany
