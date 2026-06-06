"use client"

import { Sparkles, Loader2, Bot } from "lucide-react"
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
    <div className="rounded-lg border border-dashed border-primary/25 bg-primary/5 p-5 space-y-3">
      <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
        <Bot className="size-4 text-primary/60" />
        Analisi contestuale non ancora generata
      </div>
      <p className="text-sm text-muted-foreground leading-relaxed">
        Il Generator Agent produrrà un&apos;analisi in italiano con citazioni documentali verificate,
        applicando il guardrail R3 (grounding obbligatorio).
      </p>
      <Button
        variant="outline"
        size="sm"
        disabled={isPending}
        className="border-primary/30 text-primary hover:bg-primary/5"
        onClick={() => mutate({ domain, rule_id: ruleId })}
      >
        {isPending ? (
          <>
            <Loader2 className="size-4 animate-spin" />
            Generazione in corso…
          </>
        ) : (
          <>
            <Sparkles className="size-4" />
            Genera spiegazione
          </>
        )}
      </Button>
    </div>
  )
}
