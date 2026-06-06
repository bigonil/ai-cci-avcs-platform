import { Suspense } from "react"
import { IncoherenceListClient } from "./list-client"
import { IncoherenceListSkeleton } from "./loading"
import { AlertTriangle } from "lucide-react"

export default function IncoherencesPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 pb-4 border-b">
        <AlertTriangle className="size-5 text-primary" />
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Incoerenze rilevate</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Analisi deterministica di coerenza documentale per tutti i domini pilota
          </p>
        </div>
      </div>
      <Suspense fallback={<IncoherenceListSkeleton />}>
        <IncoherenceListClient />
      </Suspense>
    </div>
  )
}
