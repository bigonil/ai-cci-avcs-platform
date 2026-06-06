"use client"

import Link from "next/link"
import { useIncoherence } from "@/hooks/use-incoherences"
import { ChunkCitation } from "@/components/chunk-citation"
import { ExplanationBlock } from "@/components/explanation-block"
import { GenerateExplanationButton } from "@/components/generate-explanation-button"
import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { formatEur, formatDate, cn } from "@/lib/utils"
import { ArrowLeft, AlertTriangle, Calendar, Building2, TrendingUp, FileText, Sparkles } from "lucide-react"
import type { Severity } from "@/lib/api"

const SEVERITY_CONFIG: Record<
  Severity,
  { border: string; badge: "default" | "secondary" | "outline" | "destructive" }
> = {
  LOW:      { border: "border-l-blue-400",   badge: "secondary"   },
  MEDIUM:   { border: "border-l-yellow-500", badge: "outline"     },
  HIGH:     { border: "border-l-orange-500", badge: "default"     },
  CRITICAL: { border: "border-l-red-500",    badge: "destructive" },
}

const VALUE_LABELS: Record<string, string> = {
  delta:             "Delta / Sforamento",
  overrun_eur:       "Sforamento",
  actual:            "Valore effettivo",
  budget:            "Budget allocato",
  total:             "Totale aggregato",
  cap:               "Cap di budget",
  value_a:           "Valore A",
  value_b:           "Valore B",
  cert_valid_to:     "Certificazione valida fino al",
  commitment_end:    "Fine periodo impegno",
  gap_days:          "Gap certificazione",
  concentration_pct: "Concentrazione fornitore",
  threshold_pct:     "Soglia di allerta",
}

function formatValue(key: string, value: unknown): string {
  if (typeof value === "number") {
    const k = key.toLowerCase()
    if (k.includes("pct") || k.includes("percent")) return `${value.toFixed(1)} %`
    if (k.includes("days") || k === "gap_days") return `${value} giorni`
    return formatEur(value)
  }
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}/.test(value)) {
    return new Intl.DateTimeFormat("it-IT", { dateStyle: "long" }).format(new Date(value))
  }
  return String(value)
}

function labelFor(key: string): string {
  return (
    VALUE_LABELS[key] ??
    key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  )
}

function isDisplayable(value: unknown): boolean {
  return value !== null && value !== undefined && value !== "" && typeof value !== "object"
}

export function IncoherenceDetailClient({ id }: { id: string }) {
  const { data, isLoading, isError } = useIncoherence(id)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-44 w-full rounded-xl" />
        <Skeleton className="h-36 w-full rounded-xl" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="size-4" />
        <AlertDescription>
          Incoerenza non trovata o servizio non disponibile.
        </AlertDescription>
      </Alert>
    )
  }

  const cfg = SEVERITY_CONFIG[data.severity as Severity] ?? SEVERITY_CONFIG.MEDIUM
  const computed = data.computed_values ?? {}
  const computedEntries = Object.entries(computed).filter(([, v]) => isDisplayable(v))
  const entityAEntries = Object.entries(data.entity_a_props ?? {}).filter(([, v]) => isDisplayable(v))
  const entityBEntries = Object.entries(data.entity_b_props ?? {}).filter(([, v]) => isDisplayable(v))

  return (
    <div className="space-y-5 max-w-3xl">
      <Link href="/incoherences" className={buttonVariants({ variant: "ghost", size: "sm" })}>
        <ArrowLeft className="size-4" />
        Torna all&apos;elenco
      </Link>

      {/* Header */}
      <Card className={cn("border-l-4", cfg.border)}>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <AlertTriangle className="size-4 text-muted-foreground" />
                <CardTitle className="font-mono">{data.rule_id}</CardTitle>
              </div>
              <CardDescription>{data.description}</CardDescription>
            </div>
            <Badge variant={cfg.badge} className="shrink-0">
              {data.severity}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
            <MetaField icon={<Building2 className="size-3.5" />} label="Dominio">
              <span className="font-mono">{data.domain}</span>
            </MetaField>
            <MetaField icon={<TrendingUp className="size-3.5" />} label="Impatto stimato">
              <span className={cn("font-semibold", data.impact_eur > 0 && "text-orange-600 dark:text-orange-400")}>
                {data.impact_eur > 0 ? formatEur(data.impact_eur) : "—"}
              </span>
            </MetaField>
            <MetaField icon={<Calendar className="size-3.5" />} label="Rilevata il">
              {formatDate(data.detected_at)}
            </MetaField>
          </div>
        </CardContent>
      </Card>

      {/* Computed values — core section showing violation detail */}
      {computedEntries.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">Valori rilevati</CardTitle>
            <CardDescription className="text-xs">
              Confronto deterministico che ha prodotto questa non conformità
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="divide-y rounded-md border overflow-hidden">
              {computedEntries.map(([key, value]) => (
                <div
                  key={key}
                  className="flex items-center justify-between px-4 py-2.5 text-sm even:bg-muted/30"
                >
                  <span className="text-muted-foreground">{labelFor(key)}</span>
                  <span
                    className={cn(
                      "font-medium tabular-nums",
                      (key === "delta" || key === "overrun_eur") &&
                        "text-orange-600 dark:text-orange-400 font-semibold"
                    )}
                  >
                    {formatValue(key, value)}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Entity properties */}
      {(entityAEntries.length > 0 || entityBEntries.length > 0) && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">Entità coinvolte</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {entityAEntries.length > 0 && (
              <EntityBlock title={data.entity_a_type ?? "Entità A"} entries={entityAEntries} />
            )}
            {entityBEntries.length > 0 && (
              <>
                <Separator />
                <EntityBlock title={data.entity_b_type ?? "Entità B"} entries={entityBEntries} />
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* Evidence chunks */}
      {data.evidence_chunks.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <FileText className="size-4" />
              Chunk di evidenza ({data.evidence_chunks.length})
            </CardTitle>
            <CardDescription className="text-xs">
              Segmenti documentali che hanno prodotto questa rilevazione
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-1.5">
              {data.evidence_chunks.map((c) => (
                <ChunkCitation key={c} chunkId={c} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Explanation (Generator Agent — cache-first, on-demand generation) */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Sparkles className="size-4" />
            Spiegazione con citazioni
          </CardTitle>
          <CardDescription className="text-xs">
            Analisi contestuale prodotta dal Generator Agent (grounding R3 verificato)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data.explanation ? (
            <ExplanationBlock
              text={data.explanation.text}
              citations={data.explanation.citations}
              groundingVerified={data.explanation.grounding_verified}
            />
          ) : (
            <GenerateExplanationButton
              incoherenceId={data.id}
              domain={data.domain}
              ruleId={data.rule_id}
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function MetaField({
  icon,
  label,
  children,
}: {
  icon?: React.ReactNode
  label: string
  children: React.ReactNode
}) {
  return (
    <div>
      <p className="flex items-center gap-1 text-xs text-muted-foreground mb-0.5">
        {icon}
        {label}
      </p>
      <div className="font-medium text-sm">{children}</div>
    </div>
  )
}

function EntityBlock({
  title,
  entries,
}: {
  title: string
  entries: [string, unknown][]
}) {
  return (
    <div>
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
        {title}
      </p>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
        {entries.map(([key, value]) => (
          <div key={key}>
            <span className="text-muted-foreground">{labelFor(key)}: </span>
            <span className="font-medium">{formatValue(key, value)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
