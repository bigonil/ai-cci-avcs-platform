import { Suspense } from "react"
import { HitlQueueClient } from "./queue-client"
import { Skeleton } from "@/components/ui/skeleton"
import { ClipboardList } from "lucide-react"

export default function HitlPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 pb-4 border-b">
        <ClipboardList className="size-5 text-primary" />
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Coda Human-in-the-Loop</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Azioni ad alto impatto che richiedono approvazione umana esplicita (R6)
          </p>
        </div>
      </div>
      <Suspense fallback={<Skeleton className="h-48 w-full rounded-xl" />}>
        <HitlQueueClient />
      </Suspense>
    </div>
  )
}
