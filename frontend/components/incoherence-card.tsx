"use client"

import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { formatEur } from "@/lib/utils"
import { cn } from "@/lib/utils"
import { AlertTriangle, FileText, ChevronRight } from "lucide-react"
import type { Incoherence, Severity } from "@/lib/api"

const SEVERITY_CONFIG: Record<
  Severity,
  { border: string; badge: "default" | "secondary" | "outline" | "destructive" }
> = {
  LOW:      { border: "border-l-blue-400",   badge: "secondary"   },
  MEDIUM:   { border: "border-l-yellow-500", badge: "outline"     },
  HIGH:     { border: "border-l-orange-500", badge: "default"     },
  CRITICAL: { border: "border-l-red-500",    badge: "destructive" },
}

interface IncoherenceCardProps {
  incoherence: Incoherence
  onSelect: (id: string) => void
  compact?: boolean
}

export function IncoherenceCard({ incoherence, onSelect, compact = false }: IncoherenceCardProps) {
  const cfg = SEVERITY_CONFIG[incoherence.severity] ?? SEVERITY_CONFIG.MEDIUM
  const computed = incoherence.computed_values ?? {}

  const previewDelta =
    typeof computed["delta"] === "number"         ? computed["delta"] as number
    : typeof computed["overrun_eur"] === "number" ? computed["overrun_eur"] as number
    : incoherence.impact_eur > 0                  ? incoherence.impact_eur
    : null

  return (
    <Card className={cn("border-l-4 transition-colors hover:bg-muted/30", cfg.border)}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <AlertTriangle className="size-4 shrink-0 text-muted-foreground" />
            <span className="font-mono text-sm font-semibold">{incoherence.rule_id}</span>
            <span className="text-xs text-muted-foreground font-mono hidden sm:inline">
              · {incoherence.domain}
            </span>
          </div>
          <Badge variant={cfg.badge} className="shrink-0">
            {incoherence.severity}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        <p className="text-sm leading-snug">{incoherence.description}</p>

        {!compact && (
          <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-muted-foreground">
            {previewDelta !== null && (
              <span className="font-medium text-foreground">
                Δ {formatEur(previewDelta)}
              </span>
            )}
            {incoherence.evidence_chunks.length > 0 && (
              <span className="flex items-center gap-1">
                <FileText className="size-3" />
                {incoherence.evidence_chunks.length} chunk evidenza
              </span>
            )}
          </div>
        )}

        <div className="flex justify-end pt-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1 text-xs"
            onClick={() => onSelect(incoherence.id)}
          >
            Dettaglio
            <ChevronRight className="size-3" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
