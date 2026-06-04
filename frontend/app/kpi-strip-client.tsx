"use client"

import { useIncoherences } from "@/hooks/use-incoherences"
import { useHitlQueue } from "@/hooks/use-hitl-queue"
import { KpiStrip } from "@/components/kpi-strip"

export function KpiStripClient() {
  const { data: incoherences, isLoading: l1 } = useIncoherences({ domain: "hera_it", limit: 100 })
  const { data: hitlQueue, isLoading: l2 } = useHitlQueue()

  const criticalCount = incoherences?.filter((i) => i.severity === "CRITICAL").length ?? 0
  const highCount = incoherences?.filter((i) => i.severity === "HIGH").length ?? 0

  return (
    <KpiStrip
      totalIncoherences={incoherences?.length}
      criticalCount={criticalCount}
      highCount={highCount}
      pendingHitl={hitlQueue?.length}
      loading={l1 || l2}
    />
  )
}
