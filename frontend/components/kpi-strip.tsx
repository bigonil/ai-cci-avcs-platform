import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertTriangle, ClipboardCheck, ShieldCheck } from "lucide-react"

interface KpiStripProps {
  totalIncoherences?: number
  pendingHitl?: number
  chainValid?: boolean
  loading?: boolean
}

export function KpiStrip({
  totalIncoherences,
  pendingHitl,
  chainValid,
  loading = false,
}: KpiStripProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <KpiCard
        label="Incoerenze rilevate"
        icon={<AlertTriangle className="size-4 text-muted-foreground" />}
        loading={loading}
      >
        <span className="text-2xl font-bold">
          {totalIncoherences ?? "—"}
        </span>
      </KpiCard>

      <KpiCard
        label="Azioni HITL in attesa"
        icon={<ClipboardCheck className="size-4 text-muted-foreground" />}
        loading={loading}
      >
        <span className="text-2xl font-bold">
          {pendingHitl ?? "—"}
        </span>
      </KpiCard>

      <KpiCard
        label="Integrità audit chain"
        icon={<ShieldCheck className="size-4 text-muted-foreground" />}
        loading={loading}
      >
        {chainValid == null ? (
          <span className="text-2xl font-bold">—</span>
        ) : (
          <span
            className={`text-2xl font-bold ${chainValid ? "text-green-600 dark:text-green-400" : "text-destructive"}`}
          >
            {chainValid ? "OK" : "ERRORE"}
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
    <Card size="sm">
      <CardHeader className="border-b">
        <div className="flex items-center gap-2">
          {icon}
          <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
            {label}
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="pt-3">
        {loading ? <Skeleton className="h-8 w-16" /> : children}
      </CardContent>
    </Card>
  )
}
