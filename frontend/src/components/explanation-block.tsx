import type { ReactNode } from 'react'
import { CheckCircle2 } from 'lucide-react'
import { ChunkCitation } from './chunk-citation'

function renderTextWithCitations(text: string): ReactNode[] {
  const parts = text.split(/(\[source:\s*[^\]]+\])/g)
  return parts.map((part, i) => {
    const match = part.match(/\[source:\s*([^\]]+)\]/)
    if (match) {
      return <ChunkCitation key={i} chunkId={match[1]!.trim()} />
    }
    return <span key={i}>{part}</span>
  })
}

interface ExplanationBlockProps {
  explanation: string
  citations: string[]
  groundingVerified: boolean
}

export function ExplanationBlock({ explanation, citations, groundingVerified }: ExplanationBlockProps) {
  return (
    <div style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 10, padding: 16 }}>
      {groundingVerified && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10, fontSize: 10, color: '#4ade80' }}>
          <CheckCircle2 size={12} />
          Grounding verificato · tutte le citazioni da documenti indicizzati
        </div>
      )}

      <p style={{ fontSize: 13, lineHeight: 1.7, color: '#e2e8f0', margin: 0 }}>
        {renderTextWithCitations(explanation)}
      </p>

      {citations.length > 0 && (
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ fontSize: 9, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 6 }}>Fonti</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {citations.map((c) => (
              <ChunkCitation key={c} chunkId={c} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
