"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { CoherenceService } from "@/lib/api"

export function useGenerateExplanation(incoherenceId: string) {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: ({
      domain,
      rule_id,
    }: {
      domain: string
      rule_id: string
    }) => CoherenceService.generateExplanation(incoherenceId, domain, rule_id),

    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["incoherence", incoherenceId] })
    },

    onError: (err: Error) => {
      toast.error("Errore generazione spiegazione", {
        description: err.message || "Servizio non disponibile. Riprova tra qualche secondo.",
      })
    },
  })
}
