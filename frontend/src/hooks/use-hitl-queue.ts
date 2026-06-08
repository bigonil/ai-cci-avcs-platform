// frontend/src/hooks/use-hitl-queue.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import type { HitlAction } from '@/lib/types'

export function useHitlQueue() {
  return useQuery({
    queryKey: ['hitl-queue'],
    queryFn: () => apiFetch<HitlAction[]>('/hitl/queue'),
  })
}

export function useHitlAction(id: string) {
  return useQuery({
    queryKey: ['hitl-action', id],
    queryFn: () => apiFetch<HitlAction>(`/hitl/${id}`),
    enabled: Boolean(id),
  })
}

export function useApproveHitl() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, motivation }: { id: string; motivation: string }) =>
      apiFetch(`/hitl/${id}/approve`, {
        method: 'POST',
        body: JSON.stringify({ motivation }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['hitl-queue'] })
      qc.invalidateQueries({ queryKey: ['incoherences'] })
    },
  })
}

export function useRejectHitl() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, motivation }: { id: string; motivation: string }) =>
      apiFetch(`/hitl/${id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ motivation }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['hitl-queue'] })
    },
  })
}
