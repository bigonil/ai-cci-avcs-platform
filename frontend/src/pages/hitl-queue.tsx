// frontend/src/pages/hitl-queue.tsx
import { Link } from 'react-router-dom'
import { ClipboardList, Clock } from 'lucide-react'
import { useHitlQueue } from '@/hooks/use-hitl-queue'
import { formatDate } from '@/lib/utils'

export function HitlQueue() {
  const { data: actions, isLoading } = useHitlQueue()

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <ClipboardList size={18} color="var(--color-medium)" />
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#f1f5f9', letterSpacing: '-0.3px', margin: 0 }}>Coda HITL</h1>
        </div>
        <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
          Azioni che richiedono approvazione umana (R6)
        </p>
      </div>

      {isLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[1, 2].map((i) => <div key={i} className="animate-pulse" style={{ height: 80, background: 'var(--card-bg)', borderRadius: 10 }} />)}
        </div>
      )}

      {!isLoading && (!actions || actions.length === 0) && (
        <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-dim)', fontSize: 13 }}>
          Nessuna azione in attesa ✓
        </div>
      )}

      {!isLoading && actions?.map((action) => (
        <Link key={action.id} to={`/hitl/${action.id}`} style={{ textDecoration: 'none' }}>
          <div style={{ background: 'var(--card-bg)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: 10, padding: '14px 16px', marginBottom: 8, cursor: 'pointer', transition: 'all 0.15s' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#f1f5f9' }}>{action.action_type}</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: '#fcd34d' }}>
                <Clock size={10} />
                In attesa
              </span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>{action.description}</div>
            <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>
              Creata {formatDate(action.created_at)} · Impatto: {action.impact}
            </div>
          </div>
        </Link>
      ))}
    </div>
  )
}
