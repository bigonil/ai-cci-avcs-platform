// frontend/src/hooks/use-explanation.ts
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import type { ExplanationOut } from '@/lib/types'

export function useExplanation(incoherenceId: string) {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: () =>
      apiFetch<ExplanationOut>(`/incoherences/${incoherenceId}/explain`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['incoherence', incoherenceId] })
    },
  })
}
