"use client"

import { useMutation, useQuery } from "@tanstack/react-query"
import { GovernanceService } from "@/lib/api"

export function useAuditByCorrelation(correlationId: string) {
  return useQuery({
    queryKey: ["audit", correlationId],
    queryFn: () => GovernanceService.getAuditByCorrelation(correlationId),
    enabled: Boolean(correlationId),
  })
}

export function useVerifyChain() {
  return useMutation({
    mutationFn: () => GovernanceService.verifyChain(),
  })
}
