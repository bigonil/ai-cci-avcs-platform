import Link from "next/link"
import { Suspense } from "react"
import { KpiStripClient } from "./kpi-strip-client"
import { RecentIncoherencesClient } from "./recent-incoherences-client"
import { Skeleton } from "@/components/ui/skeleton"
import { buttonVariants } from "@/components/ui/button"
import { ArrowRight, Activity, Zap } from "lucide-react"

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      {/* Hero header */}
      <div className="flex items-start justify-between gap-4 pb-2 border-b">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Activity className="size-5 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          </div>
          <p className="text-sm text-muted-foreground max-w-xl">
            Continuous Coherence Intelligence — verifica continua di coerenza finanziaria, documentale e di compliance.
          </p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground shrink-0 pt-1 bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/20 rounded-full px-3 py-1">
          <span className="inline-flex h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
          Sistema operativo
        </div>
      </div>

      {/* KPI strip */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Zap className="size-4 text-primary" />
          <h2 className="text-sm font-semibold text-foreground/80 uppercase tracking-widest">
            Stato del sistema
          </h2>
        </div>
        <Suspense
          fallback={
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="rounded-lg border overflow-hidden">
                  <div className="h-1 bg-muted" />
                  <div className="p-5 space-y-2">
                    <Skeleton className="h-3 w-20" />
                    <Skeleton className="h-8 w-12" />
                    <Skeleton className="h-3 w-16" />
                  </div>
                </div>
              ))}
            </div>
          }
        >
          <KpiStripClient />
        </Suspense>
      </div>

      {/* Non-conformità rilevate */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold">Non conformità rilevate</h2>
            <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
              Hera IT · R001–R004
            </span>
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
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="rounded-lg border overflow-hidden">
                  <div className="h-1 bg-muted" />
                  <Skeleton className="h-20 rounded-none" />
                </div>
              ))}
            </div>
          }
        >
          <RecentIncoherencesClient />
        </Suspense>
      </section>
    </div>
  )
}
