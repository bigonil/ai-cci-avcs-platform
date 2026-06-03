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
      // Look up in any cached list query first to avoid a round-trip
      const caches = qc.getQueriesData<Incoherence[]>({ queryKey: ["incoherences"] })
      for (const [, data] of caches) {
        const hit = data?.find((inc) => inc.id === id)
        if (hit) return hit
      }
      // Not in cache: fetch full list and find by id
      const list = await CoherenceService.listIncoherences({ domain: "hera_it", limit: 200 })
      const found = list.find((inc) => inc.id === id)
      if (!found) throw new Error("Incoherence not found")
      return found
    },
    enabled: Boolean(id),
  })
}
