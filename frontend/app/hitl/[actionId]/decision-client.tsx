"use client"

import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { useHitlQueue, useApproveHitl, useRejectHitl } from "@/hooks/use-hitl-queue"
import { HitlApprovalForm } from "@/components/hitl-approval-form"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"

interface Props {
  actionId: string
}

export function HitlDecisionClient({ actionId }: Props) {
  const router = useRouter()
  const { data: queue, isLoading } = useHitlQueue()
  const approveMutation = useApproveHitl()
  const rejectMutation = useRejectHitl()

  const action = queue?.find((a) => a.id === actionId)

  if (isLoading) return <Skeleton className="h-64 w-full rounded-xl" />

  if (!action) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          Azione non trovata nella coda HITL.
        </AlertDescription>
      </Alert>
    )
  }

  const isLoading2 = approveMutation.isPending || rejectMutation.isPending

  const handleDecide = (
    decision: "approve" | "reject",
    values: { decided_by: string; motivation: string }
  ) => {
    const body = { decided_by: values.decided_by, motivation: values.motivation }
    const mutate = decision === "approve" ? approveMutation : rejectMutation
    mutate.mutate(
      { id: actionId, body },
      {
        onSuccess: () => {
          toast.success(decision === "approve" ? "Azione approvata." : "Azione rifiutata.")
          router.push("/hitl")
        },
        onError: (err) => {
          toast.error(`Errore: ${err.message}`)
        },
      }
    )
  }

  return (
    <Card className="max-w-lg">
      <CardHeader className="border-b">
        <CardTitle className="text-base">Dettaglio azione</CardTitle>
      </CardHeader>
      <CardContent className="pt-4">
        <HitlApprovalForm
          action={action}
          onDecide={handleDecide}
          isLoading={isLoading2}
        />
      </CardContent>
    </Card>
  )
}
