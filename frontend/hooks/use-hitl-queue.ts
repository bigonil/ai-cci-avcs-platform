"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { GovernanceService } from "@/lib/api"
import type { HitlDecisionPayload } from "@/lib/api"

export function useHitlQueue() {
  return useQuery({
    queryKey: ["hitl-pending"],
    queryFn: () => GovernanceService.listPendingHitl(),
    refetchInterval: 15_000,
  })
}

export function useApproveHitl() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: HitlDecisionPayload }) =>
      GovernanceService.approveAction(id, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["hitl-pending"] })
      void qc.invalidateQueries({ queryKey: ["incoherences"] })
    },
  })
}

export function useRejectHitl() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: HitlDecisionPayload }) =>
      GovernanceService.rejectAction(id, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["hitl-pending"] })
    },
  })
}
