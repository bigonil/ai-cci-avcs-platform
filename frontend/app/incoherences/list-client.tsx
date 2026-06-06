"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useIncoherences } from "@/hooks/use-incoherences"
import { IncoherenceCard } from "@/components/incoherence-card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { AlertTriangle, Building2 } from "lucide-react"
import type { Severity } from "@/lib/api"

const DOMAINS = [
  { value: "hera_it",          label: "Hera IT",       short: "H" },
  { value: "aou_clinical",     label: "AOU Modena",    short: "A" },
  { value: "semsotec_product", label: "Semsotec",      short: "S" },
  { value: "ducati_corse",     label: "Ducati Corse",  short: "D" },
  { value: "dallara",          label: "Dallara",       short: "Da" },
  { value: "prada",            label: "Prada",         short: "P" },
] as const

const SEVERITY_ORDER: Record<Severity, number> = {
  CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3,
}

export function IncoherenceListClient() {
  const router = useRouter()
  const [domain, setDomain] = useState("hera_it")
  const [severity, setSeverity] = useState<Severity | undefined>()

  const { data, isLoading, isError } = useIncoherences({
    domain,
    severity,
    limit: 50,
  })

  const sorted = data
    ? [...data].sort(
        (a, b) =>
          (SEVERITY_ORDER[a.severity] ?? 4) - (SEVERITY_ORDER[b.severity] ?? 4)
      )
    : []

  const criticalHighCount = data?.filter((i) =>
    i.severity === "CRITICAL" || i.severity === "HIGH"
  ).length ?? 0

  return (
    <div className="space-y-5">
      {/* Domain tabs */}
      <div className="space-y-1">
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-2">
          <Building2 className="size-3.5" />
          Dominio di verifica
        </div>
        <Tabs value={domain} onValueChange={(v) => { setDomain(v); setSeverity(undefined) }}>
          <TabsList className="h-auto flex-wrap gap-1 bg-muted/50 p-1">
            {DOMAINS.map((d) => (
              <TabsTrigger
                key={d.value}
                value={d.value}
                className="text-xs data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm"
              >
                {d.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      {/* Filter bar + count */}
      <div className="flex items-center gap-3 flex-wrap">
        <Select
          value={severity ?? "all"}
          onValueChange={(v) => setSeverity(v === "all" ? undefined : (v as Severity))}
        >
          <SelectTrigger className="w-44 h-8 text-xs">
            <SelectValue placeholder="Filtra severità" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tutte le severità</SelectItem>
            <SelectItem value="CRITICAL">🔴 CRITICAL</SelectItem>
            <SelectItem value="HIGH">🟠 HIGH</SelectItem>
            <SelectItem value="MEDIUM">🟡 MEDIUM</SelectItem>
            <SelectItem value="LOW">🔵 LOW</SelectItem>
          </SelectContent>
        </Select>

        {!isLoading && data != null && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>{data.length} {data.length === 1 ? "risultato" : "risultati"}</span>
            {criticalHighCount > 0 && (
              <Badge variant="destructive" className="gap-1 text-xs">
                <AlertTriangle className="size-3" />
                {criticalHighCount} urgenti
              </Badge>
            )}
          </div>
        )}
      </div>

      {/* States */}
      {isError && (
        <Alert variant="destructive">
          <AlertTriangle className="size-4" />
          <AlertDescription>
            Impossibile caricare le incoerenze. Verifica che il coherence-service sia attivo.
          </AlertDescription>
        </Alert>
      )}

      {isLoading && (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="rounded-lg border overflow-hidden">
              <div className="h-1 bg-muted" />
              <Skeleton className="h-20 rounded-none" />
            </div>
          ))}
        </div>
      )}

      {!isLoading && sorted.length === 0 && !isError && (
        <div className="rounded-xl border border-dashed py-16 text-center">
          <Building2 className="size-8 text-muted-foreground/30 mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">
            Nessuna incoerenza rilevata per questo dominio.
          </p>
        </div>
      )}

      <div className="space-y-2">
        {sorted.map((inc) => (
          <IncoherenceCard
            key={inc.id}
            incoherence={inc}
            onSelect={(id) => router.push(`/incoherences/${id}`)}
          />
        ))}
      </div>
    </div>
  )
}
