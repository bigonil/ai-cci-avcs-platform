
interface KpiStripProps {
  incoherences: number
  hitlPending: number
  auditOk: boolean
  loading: boolean
}

interface KpiCardProps {
  label: string
  value: string | number
  sub: string
  barColor: string
  valueColor: string
  loading: boolean
}

function KpiCard({ label, value, sub, barColor, valueColor, loading }: KpiCardProps) {
  return (
    <div
      style={{
        background: 'var(--card-bg)',
        border: '1px solid var(--card-border)',
        borderRadius: 12,
        overflow: 'hidden',
        backdropFilter: 'blur(8px)',
        position: 'relative',
      }}
    >
      <div style={{ height: 2, background: `linear-gradient(90deg, ${barColor}, transparent)` }} />
      <div style={{ padding: 16 }}>
        <div style={{ fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 8 }}>
          {label}
        </div>
        {loading ? (
          <div className="animate-pulse" style={{ height: 36, background: 'rgba(255,255,255,0.08)', borderRadius: 4, marginBottom: 8 }} />
        ) : (
          <div style={{ fontSize: 28, fontWeight: 700, color: valueColor, fontVariantNumeric: 'tabular-nums' }}>
            {value}
          </div>
        )}
        <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>{sub}</div>
      </div>
    </div>
  )
}

export function KpiStrip({ incoherences, hitlPending, auditOk, loading }: KpiStripProps) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14, marginBottom: 24 }}>
      <KpiCard
        label="Incoerenze"
        value={incoherences}
        sub="Rilevate"
        barColor="var(--color-critical)"
        valueColor="#f87171"
        loading={loading}
      />
      <KpiCard
        label="HITL in attesa"
        value={hitlPending}
        sub="Approvazione richiesta"
        barColor="var(--color-medium)"
        valueColor="#fcd34d"
        loading={loading}
      />
      <KpiCard
        label="Audit chain"
        value={auditOk ? '✓ OK' : '✗ ERR'}
        sub="Hash chain integra"
        barColor="var(--color-ok)"
        valueColor={auditOk ? '#4ade80' : '#f87171'}
        loading={loading}
      />
    </div>
  )
}
