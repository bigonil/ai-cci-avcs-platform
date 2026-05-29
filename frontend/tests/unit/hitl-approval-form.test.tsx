import { describe, it, expect, vi } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { HitlApprovalForm } from "@/components/hitl-approval-form"
import type { HitlAction } from "@/lib/api"

const mockAction: HitlAction = {
  id: "hitl-1",
  event_type: "hitl.action.queued.v1",
  payload: { impact_eur: 150_000, rule_id: "HERA-R002" },
  status: "pending",
  created_at: "2026-01-15T09:00:00Z",
}

describe("HitlApprovalForm", () => {
  it("renders the event type", () => {
    render(<HitlApprovalForm action={mockAction} onDecide={vi.fn()} />)
    expect(screen.getByText("hitl.action.queued.v1")).toBeInTheDocument()
  })

  it("shows validation error when motivation is too short", async () => {
    render(<HitlApprovalForm action={mockAction} onDecide={vi.fn()} />)
    await userEvent.type(screen.getByLabelText(/revisore/i), "Mario Rossi")
    await userEvent.type(screen.getByLabelText(/motivazione/i), "corta")
    await userEvent.click(screen.getByRole("button", { name: /approva/i }))
    await waitFor(() => {
      expect(screen.getByText(/almeno 20 caratteri/i)).toBeInTheDocument()
    })
  })

  it("calls onDecide with 'approve' when form is valid and approve clicked", async () => {
    const onDecide = vi.fn()
    render(<HitlApprovalForm action={mockAction} onDecide={onDecide} />)
    await userEvent.type(screen.getByLabelText(/revisore/i), "Mario Rossi")
    await userEvent.type(
      screen.getByLabelText(/motivazione/i),
      "Motivazione sufficientemente lunga per superare la validazione"
    )
    await userEvent.click(screen.getByRole("button", { name: /approva/i }))
    await waitFor(() => {
      expect(onDecide).toHaveBeenCalledWith("approve", expect.objectContaining({
        decided_by: "Mario Rossi",
        motivation: expect.stringContaining("Motivazione"),
      }))
    })
  })
})
