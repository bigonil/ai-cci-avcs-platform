import type { Incoherence, IncoherenceFilters, VerificationRequest, VerificationResponse } from "./types"

export interface ExplanationResponse {
  text: string
  citations: string[]
  grounding_verified: boolean
}

// Requests go through the Next.js API proxy (/api/coherence/...) so the browser
// always uses a same-origin URL regardless of where the coherence service runs.
const BASE_URL = "/api/coherence"

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(`CoherenceService ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export const CoherenceService = {
  listIncoherences(filters?: IncoherenceFilters): Promise<Incoherence[]> {
    const params = new URLSearchParams()
    if (filters?.domain) params.set("domain", filters.domain)
    if (filters?.severity) params.set("severity", filters.severity)
    if (filters?.limit != null) params.set("limit", String(filters.limit))
    if (filters?.offset != null) params.set("offset", String(filters.offset))
    const qs = params.toString()
    return apiFetch<Incoherence[]>(`/incoherences${qs ? `?${qs}` : ""}`)
  },

  getIncoherence(id: string, domain: string): Promise<Incoherence> {
    return apiFetch<Incoherence>(
      `/incoherences/${encodeURIComponent(id)}?domain=${encodeURIComponent(domain)}`,
    )
  },

  generateExplanation(
    id: string,
    domain: string,
    rule_id: string,
  ): Promise<ExplanationResponse> {
    return apiFetch<ExplanationResponse>(`/incoherences/${encodeURIComponent(id)}/explain`, {
      method: "POST",
      body: JSON.stringify({ domain, rule_id }),
    })
  },

  triggerVerification(req: VerificationRequest): Promise<VerificationResponse> {
    return apiFetch<VerificationResponse>("/verify", {
      method: "POST",
      body: JSON.stringify(req),
    })
  },
}
