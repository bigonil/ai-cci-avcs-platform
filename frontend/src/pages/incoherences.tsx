// frontend/src/pages/incoherences.tsx
import { useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { IncoherenceCard } from '@/components/incoherence-card'
import { useIncoherences } from '@/hooks/use-incoherences'
import type { Severity } from '@/lib/types'

const SEVERITY_OPTIONS: Array<{ value: string; label: string }> = [
  { value: '', label: 'Tutte le severity' },
  { value: 'CRITICAL', label: '🔴 CRITICAL' },
  { value: 'HIGH', label: '🟠 HIGH' },
  { value: 'MEDIUM', label: '🟡 MEDIUM' },
  { value: 'LOW', label: '🔵 LOW' },
]

export function Incoherences() {
  const [severity, setSeverity] = useState('')

  const { data, isLoading } = useIncoherences({
    severity: severity || undefined,
    size: 50,
  })

  const incoList = Array.isArray(data) ? data : (data?.items ?? [])

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <AlertTriangle size={18} color="var(--color-critical)" />
            <h1 style={{ fontSize: 22, fontWeight: 700, color: '#f1f5f9', letterSpacing: '-0.3px', margin: 0 }}>Incoerenze</h1>
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
            Non conformità rilevate dalla Coherence Engine
          </p>
        </div>

        {/* Filtro */}
        <select
          aria-label="Filtra per severity"
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          style={{
            background: 'var(--card-bg)',
            border: '1px solid var(--card-border)',
            borderRadius: 8,
            padding: '6px 12px',
            color: '#e2e8f0',
            fontSize: 12,
            cursor: 'pointer',
          }}
        >
          {SEVERITY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {/* Risultati */}
      <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 12 }}>
        {isLoading ? 'Caricamento…' : `${incoList.length} incoerenz${incoList.length === 1 ? 'a' : 'e'}`}
      </div>

      {isLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="animate-pulse" style={{ height: 56, background: 'var(--card-bg)', borderRadius: 10 }} />
          ))}
        </div>
      )}

      {!isLoading && incoList.length === 0 && (
        <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-dim)', fontSize: 13 }}>
          Nessuna incoerenza trovata per i filtri selezionati.
        </div>
      )}

      {!isLoading && incoList.map((inc) => (
        <IncoherenceCard key={inc.id} incoherence={inc} />
      ))}
    </div>
  )
}
