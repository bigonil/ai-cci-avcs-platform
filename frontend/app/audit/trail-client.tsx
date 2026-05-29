"use client"

import { useState } from "react"
import Link from "next/link"
import { useAuditByCorrelation } from "@/hooks/use-audit-trail"
import { Button, buttonVariants } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { formatDate } from "@/lib/utils"
import { ShieldCheck } from "lucide-react"

export function AuditTrailClient() {
  const [correlationId, setCorrelationId] = useState("")
  const [submitted, setSubmitted] = useState("")
  const { data, isLoading, isError } = useAuditByCorrelation(submitted)

  return (
    <div className="space-y-4">
      <div className="flex items-end gap-3">
        <div className="flex-1 space-y-1.5">
          <Label htmlFor="correlation-id">Correlation ID</Label>
          <Input
            id="correlation-id"
            placeholder="demo-hera-q1-2026"
            value={correlationId}
            onChange={(e) => setCorrelationId(e.target.value)}
          />
        </div>
        <Button
          onClick={() => setSubmitted(correlationId)}
          disabled={!correlationId}
        >
          Cerca eventi
        </Button>
        <Link href="/audit/verify" className={buttonVariants({ variant: "outline" })}>
          <ShieldCheck className="size-4" />
          Verifica catena
        </Link>
      </div>

      {isLoading && <Skeleton className="h-48 w-full rounded-xl" />}
      {isError && (
        <Alert variant="destructive">
          <AlertDescription>
            Impossibile recuperare gli eventi audit. Verifica che il governance-service sia attivo.
          </AlertDescription>
        </Alert>
      )}
      {data && (
        <div className="rounded-xl border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-16">Seq</TableHead>
                <TableHead>Evento</TableHead>
                <TableHead>Attore</TableHead>
                <TableHead>Timestamp</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground">
                    Nessun evento trovato per questo correlation ID.
                  </TableCell>
                </TableRow>
              )}
              {data.map((event) => (
                <TableRow key={event.event_id}>
                  <TableCell className="font-mono text-xs">{event.seq}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="font-mono text-xs">
                      {event.event_type}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm">{event.actor}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatDate(event.ts)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
