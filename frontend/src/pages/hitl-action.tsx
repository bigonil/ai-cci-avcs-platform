// frontend/src/pages/hitl-action.tsx
import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { toast } from 'sonner'
import { ArrowLeft, CheckCircle2, XCircle } from 'lucide-react'
import { useHitlAction, useApproveHitl, useRejectHitl } from '@/hooks/use-hitl-queue'

const MIN_MOTIVATION_LEN = 20

export function HitlAction() {
  const { actionId } = useParams<{ actionId: string }>()
  const navigate = useNavigate()
  const { data: action, isLoading } = useHitlAction(actionId ?? '')
  const approve = useApproveHitl()
  const reject = useRejectHitl()
  const [motivation, setMotivation] = useState('')

  const isValid = motivation.trim().length >= MIN_MOTIVATION_LEN
  const isPending = approve.isPending || reject.isPending

  const handleApprove = () => {
    approve.mutate({ id: actionId!, motivation }, {
      onSuccess: () => { toast.success('Azione approvata'); navigate('/hitl') },
      onError: () => toast.error('Errore durante l\'approvazione'),
    })
  }

  const handleReject = () => {
    reject.mutate({ id: actionId!, motivation }, {
      onSuccess: () => { toast.success('Azione rifiutata'); navigate('/hitl') },
      onError: () => toast.error('Errore durante il rifiuto'),
    })
  }

  if (!actionId) return <div style={{ color: 'var(--text-secondary)' }}>ID azione non valido.</div>
  if (isLoading) return <div className="animate-pulse" style={{ height: 200, background: 'var(--card-bg)', borderRadius: 10 }} />
  if (!action) return <div style={{ color: 'var(--text-secondary)' }}>Azione non trovata.</div>

  return (
    <div>
      <Link to="/hitl" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-secondary)', textDecoration: 'none', marginBottom: 20 }}>
        <ArrowLeft size={14} />
        Coda HITL
      </Link>

      <h1 style={{ fontSize: 20, fontWeight: 700, color: '#f1f5f9', marginBottom: 8 }}>{action.action_type}</h1>
      <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 24 }}>{action.description}</p>

      <div style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 10, padding: 20, marginBottom: 20 }}>
        <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
          Motivazione <span style={{ color: 'var(--color-critical)' }}>*</span>
          <span style={{ color: 'var(--text-dim)', marginLeft: 4 }}>(min. {MIN_MOTIVATION_LEN} caratteri)</span>
        </label>
        <textarea
          value={motivation}
          onChange={(e) => setMotivation(e.target.value)}
          rows={4}
          placeholder="Descrivi la motivazione della tua decisione…"
          style={{ width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid var(--card-border)', borderRadius: 8, padding: '10px 12px', color: '#e2e8f0', fontSize: 13, resize: 'vertical', fontFamily: 'inherit' }}
        />
        <div style={{ fontSize: 10, color: motivation.length < MIN_MOTIVATION_LEN ? '#f87171' : '#4ade80', marginTop: 4 }}>
          {motivation.length}/{MIN_MOTIVATION_LEN} caratteri minimi
        </div>
      </div>

      <div style={{ display: 'flex', gap: 12 }}>
        <button
          onClick={handleApprove}
          disabled={!isValid || isPending}
          style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 20px', borderRadius: 8, border: '1px solid rgba(34,197,94,0.3)', background: 'rgba(34,197,94,0.1)', color: '#4ade80', fontSize: 13, fontWeight: 500, cursor: (!isValid || isPending) ? 'not-allowed' : 'pointer', opacity: (!isValid || isPending) ? 0.5 : 1 }}
        >
          <CheckCircle2 size={14} />
          Approva
        </button>

        <button
          onClick={handleReject}
          disabled={!isValid || isPending}
          style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 20px', borderRadius: 8, border: '1px solid rgba(239,68,68,0.3)', background: 'rgba(239,68,68,0.1)', color: '#f87171', fontSize: 13, fontWeight: 500, cursor: (!isValid || isPending) ? 'not-allowed' : 'pointer', opacity: (!isValid || isPending) ? 0.5 : 1 }}
        >
          <XCircle size={14} />
          Rifiuta
        </button>
      </div>
    </div>
  )
}
