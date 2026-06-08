// frontend/src/lib/types.ts
export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'

export interface Incoherence {
  id: string
  domain: string
  rule_id: string
  severity: Severity
  description: string
  detected_at: string
  impact_eur: number
  evidence_chunks: string[]
  explanation: string | null
  citations: string[]
  grounding_verified: boolean | null
}

export interface HitlAction {
  id: string
  action_type: string
  description: string
  impact: string
  status: 'PENDING' | 'APPROVED' | 'REJECTED'
  created_at: string
  incoherence_id: string | null
}

export interface AuditEvent {
  seq: number
  event_id: string
  ts: string
  actor: string
  event_type: string
  payload: Record<string, unknown>
}

export interface AuditChainStatus {
  valid: boolean
  total_records: number
  last_seq: number
}

export interface ExplanationOut {
  explanation: string
  citations: string[]
  grounding_verified: boolean
}

export interface PagedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}
