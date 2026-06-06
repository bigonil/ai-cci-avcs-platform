"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { formatEur, formatDate, cn } from "@/lib/utils"
import { AlertTriangle, FileText, ChevronRight, Clock } from "lucide-react"
import type { Incoherence, Severity } from "@/lib/api"

const SEVERITY_CONFIG: Record<
  Severity,
  {
    bar: string
    badge: "default" | "secondary" | "outline" | "destructive"
    badgeClass: string
    icon: string
  }
> = {
  LOW:      { bar: "bg-blue-400",    badge: "secondary",   badgeClass: "text-blue-700 dark:text-blue-300",   icon: "text-blue-400"   },
  MEDIUM:   { bar: "bg-yellow-500",  badge: "outline",     badgeClass: "text-yellow-700 dark:text-yellow-300", icon: "text-yellow-500" },
  HIGH:     { bar: "bg-orange-500",  badge: "default",     badgeClass: "text-orange-700 dark:text-orange-300", icon: "text-orange-500" },
  CRITICAL: { bar: "bg-red-500",     badge: "destructive", badgeClass: "",                                   icon: "text-red-500"    },
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
    <Card
      className="overflow-hidden border transition-all hover:shadow-sm hover:-translate-y-px cursor-pointer group"
      onClick={() => onSelect(incoherence.id)}
    >
      <div className={cn("h-1 w-full", cfg.bar)} />
      <CardContent className="px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-2.5 min-w-0">
            <AlertTriangle className={cn("size-4 mt-0.5 shrink-0", cfg.icon)} />
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-mono text-sm font-semibold">{incoherence.rule_id}</span>
                <span className="text-xs text-muted-foreground hidden sm:inline opacity-60">
                  {incoherence.domain}
                </span>
              </div>
              <p className={cn("text-sm mt-0.5 leading-snug text-foreground/90", compact && "line-clamp-1")}>
                {incoherence.description}
              </p>
            </div>
          </div>
          <Badge
            variant={cfg.badge}
            className={cn("shrink-0 mt-0.5 font-medium", cfg.badgeClass)}
          >
            {incoherence.severity}
          </Badge>
        </div>

        {!compact && (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
              {previewDelta !== null && (
                <span className="font-semibold text-foreground/80">
                  Δ {formatEur(previewDelta)}
                </span>
              )}
              {incoherence.evidence_chunks.length > 0 && (
                <span className="flex items-center gap-1">
                  <FileText className="size-3" />
                  {incoherence.evidence_chunks.length} chunk
                </span>
              )}
              {incoherence.detected_at && (
                <span className="flex items-center gap-1">
                  <Clock className="size-3" />
                  {formatDate(incoherence.detected_at)}
                </span>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 text-xs text-primary opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={(e) => { e.stopPropagation(); onSelect(incoherence.id) }}
            >
              Dettaglio
              <ChevronRight className="size-3" />
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
