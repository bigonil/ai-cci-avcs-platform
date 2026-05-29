import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { IncoherenceCard } from "@/components/incoherence-card"
import type { Incoherence } from "@/lib/api"

const mockIncoherence: Incoherence = {
  id: "inc-1",
  rule_id: "HERA-R001",
  description: "Budget overrun rispetto a impegno contrattuale",
  severity: "HIGH",
  impact_eur: 200_000,
  evidence_chunks: ["doc_budget_2026_chunk_03", "doc_commitment_aws_chunk_01"],
  domain: "hera_it",
  detected_at: "2026-01-15T10:00:00Z",
}

describe("IncoherenceCard", () => {
  it("renders rule_id and severity badge", () => {
    render(<IncoherenceCard incoherence={mockIncoherence} onSelect={vi.fn()} />)
    expect(screen.getByText("HERA-R001")).toBeInTheDocument()
    expect(screen.getByText("HIGH")).toBeInTheDocument()
  })

  it("renders description", () => {
    render(<IncoherenceCard incoherence={mockIncoherence} onSelect={vi.fn()} />)
    expect(screen.getByText(/budget overrun/i)).toBeInTheDocument()
  })

  it("renders formatted impact amount", () => {
    render(<IncoherenceCard incoherence={mockIncoherence} onSelect={vi.fn()} />)
    expect(screen.getByText(/200/)).toBeInTheDocument()
  })

  it("renders evidence chunk citations", () => {
    render(<IncoherenceCard incoherence={mockIncoherence} onSelect={vi.fn()} />)
    expect(screen.getByText("doc_budget_2026_chunk_03")).toBeInTheDocument()
    expect(screen.getByText("doc_commitment_aws_chunk_01")).toBeInTheDocument()
  })

  it("calls onSelect with the incoherence id when detail button is clicked", async () => {
    const onSelect = vi.fn()
    render(<IncoherenceCard incoherence={mockIncoherence} onSelect={onSelect} />)
    await userEvent.click(screen.getByRole("button", { name: /vedi dettaglio/i }))
    expect(onSelect).toHaveBeenCalledWith("inc-1")
  })
})
