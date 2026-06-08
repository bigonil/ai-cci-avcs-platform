import { Link } from 'react-router-dom'
import type { Incoherence, Severity } from '@/lib/types'
import { formatEur } from '@/lib/utils'

const SEVERITY_STYLE: Record<Severity, { borderColor: string; badgeBg: string; badgeColor: string; badgeBorder: string }> = {
  CRITICAL: { borderColor: '#ef4444', badgeBg: 'rgba(239,68,68,.2)', badgeColor: '#fca5a5', badgeBorder: 'rgba(239,68,68,.35)' },
  HIGH:     { borderColor: '#f97316', badgeBg: 'rgba(249,115,22,.18)', badgeColor: '#fdba74', badgeBorder: 'rgba(249,115,22,.3)' },
  MEDIUM:   { borderColor: '#f59e0b', badgeBg: 'rgba(245,158,11,.18)', badgeColor: '#fcd34d', badgeBorder: 'rgba(245,158,11,.3)' },
  LOW:      { borderColor: '#818cf8', badgeBg: 'rgba(129,140,248,.18)', badgeColor: '#a5b4fc', badgeBorder: 'rgba(129,140,248,.3)' },
}

export function IncoherenceCard({ incoherence }: { incoherence: Incoherence }) {
  const style = SEVERITY_STYLE[incoherence.severity]!

  return (
    <Link
      to={`/incoherences/${incoherence.id}`}
      style={{ textDecoration: 'none' }}
    >
      <div
        style={{
          background: 'rgba(255,255,255,0.035)',
          border: '1px solid rgba(255,255,255,0.07)',
          borderRadius: 10,
          padding: '12px 14px',
          marginBottom: 8,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          cursor: 'pointer',
          transition: 'all 0.15s',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Left border */}
        <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 3, background: style.borderColor, borderRadius: '10px 0 0 10px' }} />

        {/* Body */}
        <div style={{ flex: 1, minWidth: 0, paddingLeft: 4 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#e2e8f0', letterSpacing: '0.3px', fontFamily: "'SF Mono', monospace" }}>
            {incoherence.rule_id}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {incoherence.description}
          </div>
        </div>

        {/* Delta */}
        <div style={{ fontSize: 10, fontWeight: 700, color: 'rgba(248,113,113,0.8)', flexShrink: 0, fontFamily: 'monospace' }}>
          {formatEur(incoherence.impact_eur)}
        </div>

        {/* Badge */}
        <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.5px', padding: '3px 8px', borderRadius: 20, flexShrink: 0, background: style.badgeBg, color: style.badgeColor, border: `1px solid ${style.badgeBorder}` }}>
          {incoherence.severity}
        </div>
      </div>
    </Link>
  )
}
