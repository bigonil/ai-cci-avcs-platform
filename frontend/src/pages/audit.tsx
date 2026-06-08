// frontend/src/pages/audit.tsx
import { ShieldCheck, ShieldAlert } from 'lucide-react'
import { useAuditEvents, useAuditChainStatus } from '@/hooks/use-audit-events'
import { formatDate } from '@/lib/utils'

export function Audit() {
  const { data: events, isLoading: eventsLoading } = useAuditEvents(50)
  const { data: chainStatus } = useAuditChainStatus()

  const chainOk = chainStatus?.valid ?? null

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <ShieldCheck size={18} color="var(--color-ok)" />
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#f1f5f9', letterSpacing: '-0.3px', margin: 0 }}>Audit Trail</h1>
        </div>
        <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
          Log immutabile con hash chain SHA-256 (AI Act art. 12)
        </p>
      </div>

      {/* Chain status */}
      {chainStatus && (
        <div style={{ background: chainOk ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)', border: `1px solid ${chainOk ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`, borderRadius: 10, padding: '12px 16px', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 10 }}>
          {chainOk ? <ShieldCheck size={16} color="#4ade80" /> : <ShieldAlert size={16} color="#f87171" />}
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: chainOk ? '#4ade80' : '#f87171' }}>
              {chainOk ? 'Hash chain integra' : 'Hash chain compromessa'}
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>
              {chainStatus.total_records.toLocaleString('it-IT')} eventi · ultimo seq: {chainStatus.last_seq}
            </div>
          </div>
        </div>
      )}

      {/* Events table */}
      <div style={{ fontSize: 13, fontWeight: 600, color: '#c7d2fe', marginBottom: 12 }}>Ultimi eventi</div>

      {eventsLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {[1, 2, 3, 4, 5].map((i) => <div key={i} className="animate-pulse" style={{ height: 40, background: 'var(--card-bg)', borderRadius: 6 }} />)}
        </div>
      )}

      {!eventsLoading && events?.map((evt) => (
        <div key={evt.event_id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.04)', fontSize: 11 }}>
          <span style={{ color: 'var(--text-dim)', fontVariantNumeric: 'tabular-nums', width: 60 }}>#{evt.seq}</span>
          <span style={{ color: '#818cf8', fontFamily: 'monospace', flex: 1 }}>{evt.event_type}</span>
          <span style={{ color: 'var(--text-secondary)' }}>{evt.actor}</span>
          <span style={{ color: 'var(--text-dim)' }}>{formatDate(evt.ts)}</span>
        </div>
      ))}

      {!eventsLoading && (!events || events.length === 0) && (
        <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-dim)', fontSize: 13 }}>
          Nessun evento registrato.
        </div>
      )}
    </div>
  )
}
