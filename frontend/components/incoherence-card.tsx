import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ChunkCitation } from "@/components/chunk-citation"
import { formatEur } from "@/lib/utils"
import type { Incoherence, Severity } from "@/lib/api"

const SEVERITY_VARIANT: Record<Severity, "default" | "secondary" | "outline" | "destructive"> = {
  LOW: "secondary",
  MEDIUM: "outline",
  HIGH: "default",
  CRITICAL: "destructive",
}

interface IncoherenceCardProps {
  incoherence: Incoherence
  onSelect: (id: string) => void
}

export function IncoherenceCard({ incoherence, onSelect }: IncoherenceCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-mono text-sm">{incoherence.rule_id}</CardTitle>
        <CardDescription>{incoherence.description}</CardDescription>
        <CardAction>
          <Badge variant={SEVERITY_VARIANT[incoherence.severity]}>
            {incoherence.severity}
          </Badge>
        </CardAction>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <p className="text-sm">
            Impatto stimato:{" "}
            <span className="font-medium">{formatEur(incoherence.impact_eur)}</span>
          </p>
          {incoherence.evidence_chunks.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {incoherence.evidence_chunks.map((chunkId) => (
                <ChunkCitation key={chunkId} chunkId={chunkId} />
              ))}
            </div>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onSelect(incoherence.id)}
          >
            Vedi dettaglio
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
