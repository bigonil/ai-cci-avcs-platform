import { Suspense } from "react"
import { AuditTrailClient } from "./trail-client"
import { Skeleton } from "@/components/ui/skeleton"

export default function AuditPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Audit Trail</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Registro immutabile di ogni operazione del sistema.
        </p>
      </div>
      <Suspense fallback={<Skeleton className="h-64 w-full rounded-xl" />}>
        <AuditTrailClient />
      </Suspense>
    </div>
  )
}
