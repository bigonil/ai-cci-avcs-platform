import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertTriangle, ClipboardCheck, ShieldCheck, ShieldAlert } from "lucide-react"
import { cn } from "@/lib/utils"

interface KpiStripProps {
  totalIncoherences?: number
  criticalCount?: number
  highCount?: number
  pendingHitl?: number
  chainValid?: boolean
  loading?: boolean
}

export function KpiStrip({
  totalIncoherences,
  criticalCount = 0,
  highCount = 0,
  pendingHitl,
  chainValid,
  loading = false,
}: KpiStripProps) {
  const urgentCount = criticalCount + highCount
  const hasUrgent = urgentCount > 0

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {/* Total incoherences */}
      <Card className={cn(
        "overflow-hidden border transition-colors",
        hasUrgent && "border-orange-500/30 dark:border-orange-500/20"
      )}>
        <div className={cn("h-1 w-full", hasUrgent ? "bg-orange-500" : "bg-muted")} />
        <CardContent className="pt-4 pb-5 px-5">
          {loading ? (
            <LoadingSkeleton />
          ) : (
            <>
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                  Incoerenze
                </p>
                <div className={cn(
                  "flex h-7 w-7 items-center justify-center rounded-full",
                  hasUrgent ? "bg-orange-100 dark:bg-orange-500/15" : "bg-muted"
                )}>
                  <AlertTriangle className={cn("size-3.5", hasUrgent ? "text-orange-500" : "text-muted-foreground")} />
                </div>
              </div>
              <div className="flex items-end gap-3">
                <span className={cn(
                  "text-3xl font-bold leading-none tabular-nums",
                  hasUrgent && "text-orange-600 dark:text-orange-400"
                )}>
                  {totalIncoherences ?? "—"}
                </span>
                {!loading && urgentCount > 0 && (
                  <span className="mb-0.5 text-xs font-medium text-orange-600 dark:text-orange-400">
                    {criticalCount > 0 && `${criticalCount} critica`}
                    {criticalCount > 0 && highCount > 0 && " · "}
                    {highCount > 0 && `${highCount} alta`}
                  </span>
                )}
              </div>
              {!hasUrgent && totalIncoherences != null && (
                <p className="mt-1 text-xs text-muted-foreground">Nessuna urgente</p>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* HITL pending */}
      <Card className={cn(
        "overflow-hidden border transition-colors",
        (pendingHitl ?? 0) > 0 && "border-yellow-500/30 dark:border-yellow-500/20"
      )}>
        <div className={cn("h-1 w-full", (pendingHitl ?? 0) > 0 ? "bg-yellow-500" : "bg-muted")} />
        <CardContent className="pt-4 pb-5 px-5">
          {loading ? (
            <LoadingSkeleton />
          ) : (
            <>
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                  HITL in attesa
                </p>
                <div className={cn(
                  "flex h-7 w-7 items-center justify-center rounded-full",
                  (pendingHitl ?? 0) > 0 ? "bg-yellow-100 dark:bg-yellow-500/15" : "bg-muted"
                )}>
                  <ClipboardCheck className={cn("size-3.5", (pendingHitl ?? 0) > 0 ? "text-yellow-500" : "text-muted-foreground")} />
                </div>
              </div>
              <span className={cn(
                "text-3xl font-bold leading-none tabular-nums",
                (pendingHitl ?? 0) > 0 ? "text-yellow-600 dark:text-yellow-400" : ""
              )}>
                {pendingHitl ?? "—"}
              </span>
              {(pendingHitl ?? 0) === 0 && pendingHitl != null && (
                <p className="mt-1 text-xs text-muted-foreground">Coda vuota</p>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Audit chain */}
      <Card className={cn(
        "overflow-hidden border transition-colors",
        chainValid === false && "border-destructive/40"
      )}>
        <div className={cn(
          "h-1 w-full",
          chainValid == null ? "bg-muted" : chainValid ? "bg-green-500" : "bg-destructive"
        )} />
        <CardContent className="pt-4 pb-5 px-5">
          {loading ? (
            <LoadingSkeleton />
          ) : (
            <>
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                  Audit chain
                </p>
                <div className={cn(
                  "flex h-7 w-7 items-center justify-center rounded-full",
                  chainValid === false ? "bg-red-100 dark:bg-destructive/15"
                  : chainValid ? "bg-green-100 dark:bg-green-500/15"
                  : "bg-muted"
                )}>
                  {chainValid === false
                    ? <ShieldAlert className="size-3.5 text-destructive" />
                    : <ShieldCheck className={cn("size-3.5", chainValid ? "text-green-600 dark:text-green-400" : "text-muted-foreground")} />
                  }
                </div>
              </div>
              {chainValid == null ? (
                <>
                  <span className="text-3xl font-bold leading-none text-muted-foreground">—</span>
                  <p className="mt-1 text-xs text-muted-foreground">Non verificata</p>
                </>
              ) : (
                <span className={cn(
                  "text-2xl font-bold leading-none",
                  chainValid ? "text-green-600 dark:text-green-400" : "text-destructive"
                )}>
                  {chainValid ? "✓ Integra" : "✗ Errore"}
                </span>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-2 pt-1">
      <Skeleton className="h-3 w-20" />
      <Skeleton className="h-8 w-12" />
      <Skeleton className="h-3 w-16" />
    </div>
  )
}
