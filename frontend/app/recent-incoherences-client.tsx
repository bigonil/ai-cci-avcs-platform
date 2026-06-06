"use client"

import { useRouter } from "next/navigation"
import { useIncoherences } from "@/hooks/use-incoherences"
import { IncoherenceCard } from "@/components/incoherence-card"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertTriangle } from "lucide-react"
import type { Severity } from "@/lib/api"

const SEVERITY_ORDER: Record<Severity, number> = {
  CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3,
}

export function RecentIncoherencesClient() {
  const router = useRouter()
  const { data, isLoading, isError } = useIncoherences({ domain: "hera_it", limit: 10 })

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="rounded-lg border overflow-hidden">
            <div className="h-1 bg-muted" />
            <Skeleton className="h-20 rounded-none" />
          </div>
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="size-4" />
        <AlertDescription>
          Impossibile caricare le incoerenze. Verifica che il coherence-service sia attivo.
        </AlertDescription>
      </Alert>
    )
  }

  if (!data?.length) {
    return (
      <div className="rounded-xl border border-dashed py-10 text-center">
        <p className="text-sm text-muted-foreground">Nessuna incoerenza rilevata per Hera IT.</p>
      </div>
    )
  }

  const sorted = [...data].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 4) - (SEVERITY_ORDER[b.severity] ?? 4)
  )

  return (
    <div className="space-y-2">
      {sorted.map((inc) => (
        <IncoherenceCard
          key={inc.id}
          incoherence={inc}
          onSelect={(id) => router.push(`/incoherences/${id}`)}
        />
      ))}
    </div>
  )
}
