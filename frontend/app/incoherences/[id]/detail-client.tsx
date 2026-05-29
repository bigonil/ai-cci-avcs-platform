"use client"

import Link from "next/link"
import { useIncoherence } from "@/hooks/use-incoherences"
import { ChunkCitation } from "@/components/chunk-citation"
import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { formatEur, formatDate } from "@/lib/utils"
import { ArrowLeft } from "lucide-react"
import type { Severity } from "@/lib/api"

const SEVERITY_VARIANT: Record<Severity, "default" | "secondary" | "outline" | "destructive"> = {
  LOW: "secondary",
  MEDIUM: "outline",
  HIGH: "default",
  CRITICAL: "destructive",
}

export function IncoherenceDetailClient({ id }: { id: string }) {
  const { data, isLoading, isError } = useIncoherence(id)

  if (isLoading) return <Skeleton className="h-64 w-full rounded-xl" />
  if (isError || !data) {
    return (
      <Alert variant="destructive">
        <AlertDescription>Incoerenza non trovata o servizio non disponibile.</AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-4">
      <Link href="/incoherences" className={buttonVariants({ variant: "ghost", size: "sm" })}>
        <ArrowLeft className="size-4" />
        Torna all&apos;elenco
      </Link>

      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle className="font-mono">{data.rule_id}</CardTitle>
              <CardDescription className="mt-1">{data.description}</CardDescription>
            </div>
            <Badge variant={SEVERITY_VARIANT[data.severity]}>{data.severity}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
            <div>
              <p className="text-muted-foreground">Dominio</p>
              <p className="font-mono font-medium">{data.domain}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Impatto stimato</p>
              <p className="font-medium">{formatEur(data.impact_eur)}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Rilevata il</p>
              <p className="font-medium">{formatDate(data.detected_at)}</p>
            </div>
          </div>

          {data.evidence_chunks.length > 0 && (
            <div>
              <p className="mb-2 text-sm font-medium">Chunk di evidenza</p>
              <div className="flex flex-wrap gap-1.5">
                {data.evidence_chunks.map((c) => (
                  <ChunkCitation key={c} chunkId={c} />
                ))}
              </div>
            </div>
          )}

          {data.explanation && (
            <div>
              <p className="mb-2 text-sm font-medium">Spiegazione (generata con citazioni)</p>
              <div className="rounded-lg bg-muted p-3 text-sm leading-relaxed whitespace-pre-wrap">
                {data.explanation.text}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
