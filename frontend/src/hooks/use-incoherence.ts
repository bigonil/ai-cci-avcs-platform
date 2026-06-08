// frontend/src/hooks/use-incoherence.ts
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import type { Incoherence } from '@/lib/types'

export function useIncoherence(id: string) {
  return useQuery({
    queryKey: ['incoherence', id],
    queryFn: () => apiFetch<Incoherence>(`/incoherences/${id}`),
    enabled: Boolean(id),
  })
}
