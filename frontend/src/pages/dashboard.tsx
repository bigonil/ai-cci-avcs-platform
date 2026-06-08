// frontend/src/pages/dashboard.tsx
import { KpiStrip } from '@/components/kpi-strip'
import { IncoherenceCard } from '@/components/incoherence-card'
import { useIncoherences } from '@/hooks/use-incoherences'
import { useHitlQueue } from '@/hooks/use-hitl-queue'
import { useAuditChainStatus } from '@/hooks/use-audit-events'

export function Dashboard() {
  const { data: incoData, isLoading: incoLoading } = useIncoherences({ size: 4 })
  const { data: hitlData } = useHitlQueue()
  const { data: auditData } = useAuditChainStatus()

  const incoList = Array.isArray(incoData)
    ? incoData
    : (incoData?.items ?? [])

  const incoCount = incoList.length
  const hitlCount = hitlData?.length ?? 0
  const auditOk = auditData?.valid ?? true

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#f1f5f9', letterSpacing: '-0.3px', margin: 0 }}>Dashboard</h1>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
            Continuous Coherence Intelligence · {new Date().toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' })}
          </p>
        </div>
      </div>

      {/* KPI */}
      <KpiStrip
        incoherences={incoCount}
        hitlPending={hitlCount}
        auditOk={auditOk}
        loading={incoLoading}
      />

      {/* Recent incoherences */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#c7d2fe', letterSpacing: '0.2px' }}>
          Non conformità rilevate
        </div>
        <a href="/incoherences" style={{ fontSize: 11, color: 'rgba(129,140,248,0.6)', cursor: 'pointer', textDecoration: 'none' }}>
          Vedi tutte →
        </a>
      </div>

      {incoLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse" style={{ height: 56, background: 'var(--card-bg)', borderRadius: 10 }} />
          ))}
        </div>
      )}

      {!incoLoading && incoList.length === 0 && (
        <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-dim)', fontSize: 13 }}>
          Nessuna incoerenza rilevata ✓
        </div>
      )}

      {!incoLoading && incoList.map((inc) => (
        <IncoherenceCard key={inc.id} incoherence={inc} />
      ))}
    </div>
  )
}
