// frontend/src/pages/incoherence-detail.tsx
import { useParams, Link } from 'react-router-dom'
import { toast } from 'sonner'
import { ArrowLeft } from 'lucide-react'
import { useIncoherence } from '@/hooks/use-incoherence'
import { useExplanation } from '@/hooks/use-explanation'
import { ExplanationBlock } from '@/components/explanation-block'
import { GenerateExplanationButton } from '@/components/generate-explanation-button'
import { ChunkCitation } from '@/components/chunk-citation'
import { formatDate, SEVERITY_CONFIG } from '@/lib/utils'
import type { Severity } from '@/lib/types'

export function IncoherenceDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: inco, isLoading } = useIncoherence(id ?? '')
  const explanation = useExplanation(id ?? '')

  const handleGenerate = () => {
    explanation.mutate(undefined, {
      onError: (err) => {
        const msg = err instanceof Error ? err.message : 'Errore sconosciuto'
        toast.error(msg.includes('422') ? 'Spiegazione non disponibile: citazioni insufficienti' : `Errore: ${msg}`)
      },
    })
  }

  if (isLoading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="animate-pulse" style={{ height: 80, background: 'var(--card-bg)', borderRadius: 10 }} />
        ))}
      </div>
    )
  }

  if (!inco) {
    return <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Incoerenza non trovata.</div>
  }

  const severityStyle = SEVERITY_CONFIG[inco.severity as Severity]!

  return (
    <div>
      {/* Back */}
      <Link to="/incoherences" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-secondary)', textDecoration: 'none', marginBottom: 20 }}>
        <ArrowLeft size={14} />
        Tutte le incoerenze
      </Link>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: '#f1f5f9', fontFamily: "'SF Mono', monospace", margin: 0 }}>
            {inco.rule_id}
          </h1>
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.5px', padding: '3px 10px', borderRadius: 20, background: `${severityStyle.color}33`, color: severityStyle.color, border: `1px solid ${severityStyle.color}55` }}>
            {inco.severity}
          </span>
        </div>
        <p style={{ fontSize: 14, color: 'var(--text-secondary)', margin: 0 }}>{inco.description}</p>
        <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 8 }}>
          Rilevata {formatDate(inco.detected_at)} · Dominio: {inco.domain} · Impatto: {Math.abs(inco.impact_eur).toLocaleString('it-IT')} EUR
        </div>
      </div>

      {/* Evidence chunks */}
      {inco.evidence_chunks.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 8 }}>Chunk di evidenza</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {inco.evidence_chunks.map((c) => <ChunkCitation key={c} chunkId={c} />)}
          </div>
        </div>
      )}

      {/* Explanation */}
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#c7d2fe', marginBottom: 12 }}>Spiegazione con citazioni</div>
        {inco.explanation ? (
          <ExplanationBlock
            explanation={inco.explanation}
            citations={inco.citations}
            groundingVerified={inco.grounding_verified ?? false}
          />
        ) : (
          <GenerateExplanationButton
            onGenerate={handleGenerate}
            isPending={explanation.isPending}
          />
        )}
      </div>
    </div>
  )
}
