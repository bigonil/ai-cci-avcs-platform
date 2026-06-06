"use client"

import { Sparkles, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useGenerateExplanation } from "@/hooks/use-explanation"

interface GenerateExplanationButtonProps {
  incoherenceId: string
  domain: string
  ruleId: string
}

export function GenerateExplanationButton({
  incoherenceId,
  domain,
  ruleId,
}: GenerateExplanationButtonProps) {
  const { mutate, isPending } = useGenerateExplanation(incoherenceId)

  return (
    <div className="rounded-lg border border-dashed p-4 space-y-3">
      <p className="text-sm text-muted-foreground">
        La spiegazione contestuale non è ancora disponibile per questa non conformità.
        Il Generator Agent produrrà un&apos;analisi in italiano con citazioni verificate (R3).
      </p>
      <Button
        variant="outline"
        size="sm"
        disabled={isPending}
        onClick={() => mutate({ domain, rule_id: ruleId })}
      >
        {isPending ? (
          <>
            <Loader2 className="size-4 mr-2 animate-spin" />
            Generazione in corso…
          </>
        ) : (
          <>
            <Sparkles className="size-4 mr-2" />
            Genera spiegazione
          </>
        )}
      </Button>
    </div>
  )
}
