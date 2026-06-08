// frontend/src/hooks/use-audit-events.ts
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import type { AuditEvent, AuditChainStatus } from '@/lib/types'

export function useAuditEvents(limit = 50) {
  return useQuery({
    queryKey: ['audit-events', limit],
    queryFn: () => apiFetch<AuditEvent[]>(`/audit/events?limit=${limit}`),
    staleTime: 60_000,
  })
}

export function useAuditChainStatus() {
  return useQuery({
    queryKey: ['audit-chain-status'],
    queryFn: () => apiFetch<AuditChainStatus>('/audit/chain-status'),
    staleTime: 60_000,
  })
}
