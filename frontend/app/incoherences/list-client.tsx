"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useIncoherences } from "@/hooks/use-incoherences"
import { IncoherenceCard } from "@/components/incoherence-card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { Severity } from "@/lib/api"

export function IncoherenceListClient() {
  const router = useRouter()
  const [severity, setSeverity] = useState<Severity | undefined>()
  const { data, isLoading, isError } = useIncoherences({ domain: "hera_it", severity })

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Select
          value={severity ?? "all"}
          onValueChange={(v) => setSeverity(v === "all" ? undefined : (v as Severity))}
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Severità" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tutte</SelectItem>
            <SelectItem value="CRITICAL">CRITICAL</SelectItem>
            <SelectItem value="HIGH">HIGH</SelectItem>
            <SelectItem value="MEDIUM">MEDIUM</SelectItem>
            <SelectItem value="LOW">LOW</SelectItem>
          </SelectContent>
        </Select>
        {data && (
          <span className="text-sm text-muted-foreground">
            {data.length} risultati
          </span>
        )}
      </div>

      {isError && (
        <Alert variant="destructive">
          <AlertDescription>
            Impossibile caricare le incoerenze. Verifica che il coherence-service sia attivo.
          </AlertDescription>
        </Alert>
      )}

      {!isLoading && data?.length === 0 && (
        <p className="text-sm text-muted-foreground">Nessuna incoerenza trovata.</p>
      )}

      <div className="space-y-3">
        {data?.map((inc) => (
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
