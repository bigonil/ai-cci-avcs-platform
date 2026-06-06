"use client"

import { useQuery, useQueryClient } from "@tanstack/react-query"
import { CoherenceService } from "@/lib/api"
import type { Incoherence, IncoherenceFilters } from "@/lib/api"

export function useIncoherences(filters?: IncoherenceFilters) {
  return useQuery({
    queryKey: ["incoherences", filters],
    queryFn: () => CoherenceService.listIncoherences(filters),
  })
}

export function useIncoherence(id: string) {
  const qc = useQueryClient()
  return useQuery({
    queryKey: ["incoherence", id],
    queryFn: async (): Promise<Incoherence> => {
      // Find domain from any cached list — needed for the single-item endpoint
      let domain: string | undefined
      const caches = qc.getQueriesData<Incoherence[]>({ queryKey: ["incoherences"] })
      for (const [, data] of caches) {
        const hit = data?.find((inc) => inc.id === id)
        if (hit) { domain = hit.domain; break }
      }

      if (domain) {
        // Fetch single item: includes cached explanation if previously generated
        return CoherenceService.getIncoherence(id, domain)
      }

      // Cold load (no list cache): fetch with hera_it as fallback domain
      // The user will have navigated from the list in normal usage
      const list = await CoherenceService.listIncoherences({ domain: "hera_it", limit: 200 })
      const found = list.find((inc) => inc.id === id)
      if (!found) throw new Error("Incoherence not found")
      return found
    },
    enabled: Boolean(id),
  })
}
