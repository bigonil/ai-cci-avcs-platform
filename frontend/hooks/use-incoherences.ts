"use client"

import { useQuery } from "@tanstack/react-query"
import { CoherenceService } from "@/lib/api"
import type { IncoherenceFilters } from "@/lib/api"

export function useIncoherences(filters?: IncoherenceFilters) {
  return useQuery({
    queryKey: ["incoherences", filters],
    queryFn: () => CoherenceService.listIncoherences(filters),
  })
}

export function useIncoherence(id: string) {
  return useQuery({
    queryKey: ["incoherences", id],
    queryFn: () => CoherenceService.getIncoherence(id),
    enabled: Boolean(id),
  })
}
