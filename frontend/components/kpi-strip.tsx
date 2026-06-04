import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertTriangle, ClipboardCheck, ShieldCheck } from "lucide-react"
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
  const hasUrgent = (criticalCount ?? 0) > 0 || (highCount ?? 0) > 0

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      {/* Total incoherences */}
      <KpiCard
        label="Incoerenze rilevate"
        icon={<AlertTriangle className={cn("size-4", hasUrgent ? "text-orange-500" : "text-muted-foreground")} />}
        loading={loading}
      >
        <div className="flex items-end gap-3">
          <span className={cn("text-3xl font-bold", hasUrgent && "text-orange-600 dark:text-orange-400")}>
            {totalIncoherences ?? "—"}
          </span>
          {!loading && totalIncoherences != null && totalIncoherences > 0 && (
            <div className="flex items-center gap-1.5 pb-0.5 text-xs">
              {criticalCount > 0 && (
                <span className="inline-flex items-center gap-0.5 text-red-600 dark:text-red-400 font-medium">
                  <span className="inline-flex h-2 w-2 rounded-full bg-red-500" />
                  {criticalCount} critica
                </span>
              )}
              {highCount > 0 && (
                <span className="inline-flex items-center gap-0.5 text-orange-600 dark:text-orange-400 font-medium">
                  <span className="inline-flex h-2 w-2 rounded-full bg-orange-500" />
                  {highCount} alta
                </span>
              )}
            </div>
          )}
        </div>
      </KpiCard>

      {/* HITL pending */}
      <KpiCard
        label="Azioni HITL in attesa"
        icon={<ClipboardCheck className={cn("size-4", (pendingHitl ?? 0) > 0 ? "text-yellow-500" : "text-muted-foreground")} />}
        loading={loading}
      >
        <span className={cn(
          "text-3xl font-bold",
          (pendingHitl ?? 0) > 0 ? "text-yellow-600 dark:text-yellow-400" : ""
        )}>
          {pendingHitl ?? "—"}
        </span>
        {!loading && (pendingHitl ?? 0) === 0 && (
          <p className="text-xs text-muted-foreground mt-0.5">Nessuna in coda</p>
        )}
      </KpiCard>

      {/* Audit chain */}
      <KpiCard
        label="Integrità audit chain"
        icon={<ShieldCheck className={cn("size-4", chainValid === false ? "text-destructive" : "text-muted-foreground")} />}
        loading={loading}
      >
        {chainValid == null ? (
          <div>
            <span className="text-3xl font-bold text-muted-foreground">—</span>
            <p className="text-xs text-muted-foreground mt-0.5">Non verificata</p>
          </div>
        ) : (
          <span className={cn("text-2xl font-bold", chainValid ? "text-green-600 dark:text-green-400" : "text-destructive")}>
            {chainValid ? "✓ OK" : "✗ ERRORE"}
          </span>
        )}
      </KpiCard>
    </div>
  )
}

function KpiCard({
  label,
  icon,
  loading,
  children,
}: {
  label: string
  icon: React.ReactNode
  loading: boolean
  children: React.ReactNode
}) {
  return (
    <Card>
      <CardHeader className="border-b pb-2 pt-3">
        <div className="flex items-center gap-2">
          {icon}
          <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground font-medium">
            {label}
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="pt-3 pb-4">
        {loading ? (
          <div className="space-y-1">
            <Skeleton className="h-8 w-16" />
            <Skeleton className="h-3 w-24" />
          </div>
        ) : (
          children
        )}
      </CardContent>
    </Card>
  )
}
