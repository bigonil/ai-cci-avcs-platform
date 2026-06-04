import Link from "next/link"
import { Suspense } from "react"
import { KpiStripClient } from "./kpi-strip-client"
import { RecentIncoherencesClient } from "./recent-incoherences-client"
import { Skeleton } from "@/components/ui/skeleton"
import { buttonVariants } from "@/components/ui/button"
import { ArrowRight } from "lucide-react"

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard CCI / AVCS</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Continuous Coherence Intelligence · Verifica continua di coerenza documentale
          </p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground pt-1">
          <span className="inline-flex h-2 w-2 rounded-full bg-green-500 animate-pulse" />
          Sistema operativo
        </div>
      </div>

      {/* KPI strip */}
      <Suspense
        fallback={
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
        }
      >
        <KpiStripClient />
      </Suspense>

      {/* Non-conformità rilevate */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold">Non conformità rilevate</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Dominio Hera IT · regole R001–R004
            </p>
          </div>
          <Link
            href="/incoherences"
            className={buttonVariants({ variant: "ghost", size: "sm" })}
          >
            Vedi tutte
            <ArrowRight className="size-4" />
          </Link>
        </div>
        <Suspense
          fallback={
            <div className="space-y-3">
              <Skeleton className="h-28" />
              <Skeleton className="h-28" />
              <Skeleton className="h-28" />
            </div>
          }
        >
          <RecentIncoherencesClient />
        </Suspense>
      </section>
    </div>
  )
}
