import type {
  HitlAction,
  HitlDecisionPayload,
  AuditEvent,
  ChainVerifyResponse,
} from "./types"

// Requests go through the Next.js API proxy (/api/governance/...) so the browser
// always uses a same-origin URL regardless of where the governance service runs.
const BASE_URL = "/api/governance"

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(`GovernanceService ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export const GovernanceService = {
  listPendingHitl(): Promise<HitlAction[]> {
    // Governance returns { pending: HitlAction[], count: number }
    return apiFetch<{ pending: HitlAction[]; count: number }>("/hitl/pending").then(
      (r) => r.pending,
    )
  },

  approveAction(id: string, body: HitlDecisionPayload): Promise<HitlAction> {
    return apiFetch<HitlAction>(`/hitl/${encodeURIComponent(id)}/approve`, {
      method: "POST",
      body: JSON.stringify(body),
    })
  },

  rejectAction(id: string, body: HitlDecisionPayload): Promise<HitlAction> {
    return apiFetch<HitlAction>(`/hitl/${encodeURIComponent(id)}/reject`, {
      method: "POST",
      body: JSON.stringify(body),
    })
  },

  getAuditByCorrelation(correlationId: string): Promise<AuditEvent[]> {
    return apiFetch<AuditEvent[]>(
      `/audit/by-correlation/${encodeURIComponent(correlationId)}`
    )
  },

  verifyChain(): Promise<ChainVerifyResponse> {
    return apiFetch<ChainVerifyResponse>("/audit/chain/verify")
  },
}
