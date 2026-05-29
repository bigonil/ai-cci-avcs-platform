import { Suspense } from "react"
import { HitlDecisionClient } from "./decision-client"
import { Skeleton } from "@/components/ui/skeleton"

interface Props {
  params: Promise<{ actionId: string }>
}

export default async function HitlDecisionPage({ params }: Props) {
  const { actionId } = await params
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Revisione azione HITL</h1>
      <Suspense fallback={<Skeleton className="h-64 w-full rounded-xl" />}>
        <HitlDecisionClient actionId={actionId} />
      </Suspense>
    </div>
  )
}
