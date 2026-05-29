import { Suspense } from "react"
import { IncoherenceDetailClient } from "./detail-client"
import { Skeleton } from "@/components/ui/skeleton"

interface Props {
  params: Promise<{ id: string }>
}

export default async function IncoherenceDetailPage({ params }: Props) {
  const { id } = await params
  return (
    <div className="space-y-6">
      <Suspense fallback={<Skeleton className="h-64 w-full rounded-xl" />}>
        <IncoherenceDetailClient id={id} />
      </Suspense>
    </div>
  )
}
