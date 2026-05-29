import { Suspense } from "react"
import { IncoherenceListClient } from "./list-client"
import { IncoherenceListSkeleton } from "./loading"

export const experimental_ppr = true

export default function IncoherencesPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Incoerenze rilevate</h1>
      <Suspense fallback={<IncoherenceListSkeleton />}>
        <IncoherenceListClient />
      </Suspense>
    </div>
  )
}
