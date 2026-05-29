"use client"

import Link from "next/link"
import { useHitlQueue } from "@/hooks/use-hitl-queue"
import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { formatDate } from "@/lib/utils"
import { ClipboardCheck } from "lucide-react"

export function HitlQueueClient() {
  const { data, isLoading, isError } = useHitlQueue()

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
      </div>
    )
  }
  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          Impossibile caricare la coda HITL. Verifica che il governance-service sia attivo.
        </AlertDescription>
      </Alert>
    )
  }
  if (!data?.length) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed py-12 text-center">
        <ClipboardCheck className="size-8 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Nessuna azione in attesa.</p>
      </div>
    )
  }
  return (
    <div className="space-y-3">
      {data.map((action) => (
        <Card key={action.id}>
          <CardHeader className="border-b">
            <div className="flex items-center justify-between gap-4">
              <CardTitle className="font-mono text-sm">{action.event_type}</CardTitle>
              <Badge variant="outline">{action.status}</Badge>
            </div>
          </CardHeader>
          <CardContent className="flex items-center justify-between gap-4 pt-3">
            <p className="text-xs text-muted-foreground">
              Creata il {formatDate(action.created_at)}
            </p>
            <Link href={`/hitl/${action.id}`} className={buttonVariants({ size: "sm" })}>
              Revisiona
            </Link>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
