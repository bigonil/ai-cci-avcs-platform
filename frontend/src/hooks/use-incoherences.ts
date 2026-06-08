// frontend/src/hooks/use-incoherences.ts
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import type { Incoherence, PagedResponse } from '@/lib/types'

interface IncoherenceFilters {
  domain?: string
  severity?: string
  page?: number
  size?: number
}

export function useIncoherences(filters: IncoherenceFilters = {}) {
  const params = new URLSearchParams()
  if (filters.domain) params.set('domain', filters.domain)
  if (filters.severity) params.set('severity', filters.severity)
  if (filters.page != null) params.set('page', String(filters.page))
  if (filters.size != null) params.set('size', String(filters.size))

  const qs = params.toString() ? `?${params.toString()}` : ''

  return useQuery({
    queryKey: ['incoherences', filters],
    queryFn: () => apiFetch<PagedResponse<Incoherence> | Incoherence[]>(`/incoherences${qs}`),
  })
}
