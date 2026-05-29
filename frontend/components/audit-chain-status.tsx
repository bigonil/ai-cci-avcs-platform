"use client"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"
import { useVerifyChain } from "@/hooks/use-audit-trail"
import { ShieldCheck, ShieldAlert, RefreshCw } from "lucide-react"
import type { ChainVerifyResponse } from "@/lib/api"

export function AuditChainStatus() {
  const { mutate, data, isPending } = useVerifyChain()

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button
          variant="outline"
          size="sm"
          onClick={() => mutate()}
          disabled={isPending}
        >
          <RefreshCw className={`size-4 ${isPending ? "animate-spin" : ""}`} />
          Verifica catena hash
        </Button>
        {data && <ChainBadge report={data} />}
      </div>
      {isPending && <Skeleton className="h-20 w-full" />}
      {data && <ChainReport report={data} />}
    </div>
  )
}

function ChainBadge({ report }: { report: ChainVerifyResponse }) {
  return report.valid ? (
    <Badge variant="secondary" className="gap-1 text-green-700 dark:text-green-400">
      <ShieldCheck className="size-3" /> Integrità verificata
    </Badge>
  ) : (
    <Badge variant="destructive" className="gap-1">
      <ShieldAlert className="size-3" /> Catena compromessa
    </Badge>
  )
}

function ChainReport({ report }: { report: ChainVerifyResponse }) {
  return (
    <div className="space-y-2 text-sm">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label="Record totali" value={String(report.total_records)} />
        <Stat label="Primo seq" value={String(report.first_seq ?? "—")} />
        <Stat label="Ultimo seq" value={String(report.last_seq ?? "—")} />
        <Stat label="Tail coerente" value={report.tail_consistent ? "Sì" : "No"} />
      </div>
      {report.broken_links.length > 0 && (
        <Alert variant="destructive">
          <AlertDescription>
            <p className="mb-1 font-medium">Link interrotti ({report.broken_links.length}):</p>
            {report.broken_links.map((l) => (
              <p key={l.seq} className="font-mono text-xs">
                seq {l.seq}: {l.reason}
              </p>
            ))}
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border p-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  )
}
