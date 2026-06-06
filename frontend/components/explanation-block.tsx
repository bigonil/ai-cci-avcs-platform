import { Badge } from "@/components/ui/badge"
import { CheckCircle2, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"

interface ExplanationBlockProps {
  text: string
  citations: string[]
  groundingVerified?: boolean
}

function renderWithCitations(text: string): React.ReactNode[] {
  // Replace [source: chunk_id] with inline badge
  const parts = text.split(/(\[source:\s*[A-Za-z0-9_#\-]+\])/g)
  return parts.map((part, i) => {
    const match = part.match(/\[source:\s*([A-Za-z0-9_#\-]+)\]/)
    if (match) {
      return (
        <Badge
          key={i}
          variant="outline"
          className="mx-0.5 font-mono text-[10px] px-1.5 py-0 align-middle text-blue-700 border-blue-300 dark:text-blue-400 dark:border-blue-700"
        >
          {match[1]}
        </Badge>
      )
    }
    return <span key={i}>{part}</span>
  })
}

export function ExplanationBlock({ text, citations, groundingVerified = true }: ExplanationBlockProps) {
  return (
    <div className="space-y-3">
      <div
        className={cn(
          "rounded-lg border p-4 text-sm leading-relaxed",
          groundingVerified
            ? "bg-muted/40 border-muted"
            : "bg-yellow-50 border-yellow-200 dark:bg-yellow-950/20 dark:border-yellow-800",
        )}
      >
        <div className="whitespace-pre-wrap">{renderWithCitations(text)}</div>
      </div>

      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-1.5 text-xs">
          {groundingVerified ? (
            <>
              <CheckCircle2 className="size-3.5 text-green-600 dark:text-green-400" />
              <span className="text-green-700 dark:text-green-400">Grounding verificato (R3)</span>
            </>
          ) : (
            <>
              <AlertCircle className="size-3.5 text-yellow-600 dark:text-yellow-400" />
              <span className="text-yellow-700 dark:text-yellow-400">Citazioni parziali</span>
            </>
          )}
        </div>

        {citations.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {citations.map((c) => (
              <Badge
                key={c}
                variant="secondary"
                className="font-mono text-[10px] px-1.5 py-0"
              >
                {c}
              </Badge>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
