"use client"

import { useRouter } from "next/navigation"
import { useIncoherences } from "@/hooks/use-incoherences"
import { IncoherenceCard } from "@/components/incoherence-card"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"

export function RecentIncoherencesClient() {
  const router = useRouter()
  const { data, isLoading, isError } = useIncoherences({ domain: "hera_it", limit: 5 })

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
      </div>
    )
  }
  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertDescription>Impossibile caricare le incoerenze. Verifica che il coherence-service sia attivo.</AlertDescription>
      </Alert>
    )
  }
  if (!data?.length) {
    return <p className="text-sm text-muted-foreground">Nessuna incoerenza rilevata.</p>
  }
  return (
    <div className="space-y-3">
      {data.map((inc) => (
        <IncoherenceCard
          key={inc.id}
          incoherence={inc}
          onSelect={(id) => router.push(`/incoherences/${id}`)}
        />
      ))}
    </div>
  )
}
