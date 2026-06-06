export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"

export interface Incoherence {
  id: string
  rule_id: string
  description: string
  severity: Severity
  impact_eur: number
  evidence_chunks: string[]
  domain: string
  detected_at: string
  computed_values?: Record<string, unknown>
  entity_a_type?: string | null
  entity_a_props?: Record<string, unknown>
  entity_b_type?: string | null
  entity_b_props?: Record<string, unknown> | null
  explanation?: {
    text: string
    citations: string[]
    grounding_verified?: boolean
  }
}

export interface IncoherenceFilters {
  domain?: string
  severity?: Severity
  limit?: number
  offset?: number
}

export interface VerificationRequest {
  domain: string
  correlation_id?: string
  trigger?: { type: string; period?: string }
}

export interface VerificationResponse {
  correlation_id: string
  status: string
}

export type HitlStatus = "pending" | "approved" | "rejected"

export interface HitlAction {
  id: string
  event_type: string
  payload: Record<string, unknown>
  status: HitlStatus
  created_at: string
  decided_at?: string
  decided_by?: string
  motivation?: string
}

export interface HitlDecisionPayload {
  decided_by: string
  motivation: string
}

export interface AuditEvent {
  seq: number
  event_id: string
  correlation_id?: string
  ts: string
  actor: string
  event_type: string
  payload: Record<string, unknown>
}

export interface BrokenLink {
  seq: number
  reason: string
  expected?: string
  found?: string
}

export interface ChainVerifyResponse {
  valid: boolean
  total_records: number
  first_seq?: number
  last_seq?: number
  tail_consistent: boolean
  broken_links: BrokenLink[]
}
