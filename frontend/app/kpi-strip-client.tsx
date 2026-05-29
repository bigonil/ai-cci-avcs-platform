"use client"

import { useIncoherences } from "@/hooks/use-incoherences"
import { useHitlQueue } from "@/hooks/use-hitl-queue"
import { KpiStrip } from "@/components/kpi-strip"

export function KpiStripClient() {
  const { data: incoherences, isLoading: l1 } = useIncoherences({ domain: "hera_it", limit: 100 })
  const { data: hitlQueue, isLoading: l2 } = useHitlQueue()

  return (
    <KpiStrip
      totalIncoherences={incoherences?.length}
      pendingHitl={hitlQueue?.length}
      loading={l1 || l2}
    />
  )
}
