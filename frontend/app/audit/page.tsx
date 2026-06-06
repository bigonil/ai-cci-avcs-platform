import { Suspense } from "react"
import { AuditTrailClient } from "./trail-client"
import { Skeleton } from "@/components/ui/skeleton"
import { ShieldCheck } from "lucide-react"

export default function AuditPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 pb-4 border-b">
        <ShieldCheck className="size-5 text-primary" />
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Audit Trail</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Registro immutabile con hash chain SHA-256 — ogni operazione è tracciata e verificabile
          </p>
        </div>
      </div>
      <Suspense fallback={<Skeleton className="h-64 w-full rounded-xl" />}>
        <AuditTrailClient />
      </Suspense>
    </div>
  )
}
