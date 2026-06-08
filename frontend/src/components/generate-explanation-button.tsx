// frontend/src/components/generate-explanation-button.tsx
import { Sparkles, Loader2 } from 'lucide-react'

interface GenerateExplanationButtonProps {
  onGenerate: () => void
  isPending: boolean
}

export function GenerateExplanationButton({ onGenerate, isPending }: GenerateExplanationButtonProps) {
  return (
    <div
      style={{
        background: 'rgba(129,140,248,0.05)',
        border: '1px dashed rgba(129,140,248,0.25)',
        borderRadius: 10,
        padding: 20,
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12 }}>
        Nessuna spiegazione generata per questa incoerenza.
      </div>
      <button
        onClick={onGenerate}
        disabled={isPending}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
          padding: '8px 16px',
          borderRadius: 8,
          border: '1px solid rgba(129,140,248,0.3)',
          background: 'rgba(129,140,248,0.1)',
          color: '#a5b4fc',
          fontSize: 13,
          fontWeight: 500,
          cursor: isPending ? 'not-allowed' : 'pointer',
          opacity: isPending ? 0.7 : 1,
          transition: 'all 0.15s',
        }}
      >
        {isPending ? (
          <>
            <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
            Generazione in corso…
          </>
        ) : (
          <>
            <Sparkles size={14} />
            Genera spiegazione
          </>
        )}
      </button>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
