import { Suspense } from "react"
import { KpiStripClient } from "./kpi-strip-client"
import { RecentIncoherencesClient } from "./recent-incoherences-client"
import { Skeleton } from "@/components/ui/skeleton"

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <Suspense fallback={<div className="grid grid-cols-3 gap-4"><Skeleton className="h-24" /><Skeleton className="h-24" /><Skeleton className="h-24" /></div>}>
        <KpiStripClient />
      </Suspense>
      <section>
        <h2 className="mb-3 text-base font-medium text-muted-foreground">
          Incoerenze recenti
        </h2>
        <Suspense fallback={<div className="space-y-3"><Skeleton className="h-28" /><Skeleton className="h-28" /></div>}>
          <RecentIncoherencesClient />
        </Suspense>
      </section>
    </div>
  )
}
