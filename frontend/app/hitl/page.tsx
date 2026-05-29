import { Suspense } from "react"
import { HitlQueueClient } from "./queue-client"
import { Skeleton } from "@/components/ui/skeleton"

export default function HitlPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Coda Human-in-the-Loop</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Azioni ad alto impatto che richiedono approvazione umana esplicita.
        </p>
      </div>
      <Suspense fallback={<Skeleton className="h-48 w-full rounded-xl" />}>
        <HitlQueueClient />
      </Suspense>
    </div>
  )
}
