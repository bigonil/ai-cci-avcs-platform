"use client"

import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { formatEur, cn } from "@/lib/utils"
import type { HitlAction } from "@/lib/api"
import { CheckCircle2, XCircle, Info } from "lucide-react"

const schema = z.object({
  decided_by: z.string().min(1, "Campo obbligatorio"),
  motivation: z.string().min(20, "La motivazione deve essere di almeno 20 caratteri"),
})
type FormValues = z.infer<typeof schema>

interface HitlApprovalFormProps {
  action: HitlAction
  onDecide: (decision: "approve" | "reject", values: FormValues) => void
  isLoading?: boolean
}

export function HitlApprovalForm({ action, onDecide, isLoading }: HitlApprovalFormProps) {
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const motivationValue = watch("motivation") ?? ""
  const impact = typeof action.payload["impact_eur"] === "number"
    ? action.payload["impact_eur"] as number
    : null

  return (
    <div className="space-y-4">
      <Alert>
        <Info className="size-4" />
        <AlertDescription>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Tipo azione:</span>
              <Badge variant="outline" className="font-mono text-xs">
                {action.event_type}
              </Badge>
            </div>
            {impact != null && (
              <div className="text-sm">
                Impatto finanziario:{" "}
                <span className="font-semibold text-orange-600 dark:text-orange-400">
                  {formatEur(impact)}
                </span>
              </div>
            )}
          </div>
        </AlertDescription>
      </Alert>

      <form
        onSubmit={handleSubmit((values) => onDecide("approve", values))}
        className="space-y-4"
        noValidate
      >
        <div className="space-y-1.5">
          <Label htmlFor="decided_by">Revisore</Label>
          <Input
            id="decided_by"
            placeholder="Nome.Cognome"
            {...register("decided_by")}
            aria-invalid={Boolean(errors.decided_by)}
          />
          {errors.decided_by && (
            <p className="text-xs text-destructive">{errors.decided_by.message}</p>
          )}
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <Label htmlFor="motivation">Motivazione</Label>
            <span className={cn(
              "text-xs",
              motivationValue.length >= 20 ? "text-muted-foreground" : "text-orange-500"
            )}>
              {motivationValue.length} / 20 min
            </span>
          </div>
          <textarea
            id="motivation"
            rows={4}
            placeholder="Descrivere la motivazione della decisione (min. 20 caratteri)"
            className={cn(
              "flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm",
              "ring-offset-background placeholder:text-muted-foreground",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
              "disabled:cursor-not-allowed disabled:opacity-50 resize-none",
              errors.motivation && "border-destructive"
            )}
            {...register("motivation")}
            aria-invalid={Boolean(errors.motivation)}
          />
          {errors.motivation && (
            <p className="text-xs text-destructive">{errors.motivation.message}</p>
          )}
        </div>

        <div className="flex gap-2 pt-2">
          <Button type="submit" disabled={isLoading} className="flex-1">
            <CheckCircle2 className="size-4" />
            Approva
          </Button>
          <Button
            type="button"
            variant="destructive"
            disabled={isLoading}
            className="flex-1"
            onClick={handleSubmit((values) => onDecide("reject", values))}
          >
            <XCircle className="size-4" />
            Rifiuta
          </Button>
        </div>
      </form>
    </div>
  )
}
