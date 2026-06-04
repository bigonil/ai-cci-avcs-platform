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
import { AlertTriangle } from "lucide-react"
import type { Severity } from "@/lib/api"

const DOMAINS = [
  { value: "hera_it",          label: "Hera IT"      },
  { value: "aou_clinical",     label: "AOU Modena"   },
  { value: "semsotec_product", label: "Semsotec"     },
  { value: "ducati_corse",     label: "Ducati Corse" },
  { value: "dallara",          label: "Dallara"      },
  { value: "prada",            label: "Prada"        },
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
    <div className="space-y-4">
      {/* Domain tabs */}
      <Tabs value={domain} onValueChange={(v) => { setDomain(v); setSeverity(undefined) }}>
        <TabsList className="h-auto flex-wrap">
          {DOMAINS.map((d) => (
            <TabsTrigger key={d.value} value={d.value} className="text-xs">
              {d.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {/* Filter bar + count */}
      <div className="flex items-center gap-3 flex-wrap">
        <Select
          value={severity ?? "all"}
          onValueChange={(v) => setSeverity(v === "all" ? undefined : (v as Severity))}
        >
          <SelectTrigger className="w-40 h-8 text-xs">
            <SelectValue placeholder="Filtra severità" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tutte le severità</SelectItem>
            <SelectItem value="CRITICAL">CRITICAL</SelectItem>
            <SelectItem value="HIGH">HIGH</SelectItem>
            <SelectItem value="MEDIUM">MEDIUM</SelectItem>
            <SelectItem value="LOW">LOW</SelectItem>
          </SelectContent>
        </Select>

        {!isLoading && data != null && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>{data.length} risultati</span>
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
        <div className="space-y-3">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
      )}

      {!isLoading && sorted.length === 0 && !isError && (
        <div className="rounded-xl border border-dashed py-12 text-center">
          <p className="text-sm text-muted-foreground">
            Nessuna incoerenza rilevata per questo dominio.
          </p>
        </div>
      )}

      <div className="space-y-3">
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
