import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { KpiStrip } from "@/components/kpi-strip"

describe("KpiStrip", () => {
  it("renders all three KPI labels", () => {
    render(<KpiStrip />)
    expect(screen.getByText(/incoerenze rilevate/i)).toBeInTheDocument()
    expect(screen.getByText(/azioni hitl/i)).toBeInTheDocument()
    expect(screen.getByText(/integrità audit/i)).toBeInTheDocument()
  })

  it("shows dashes when values are undefined", () => {
    render(<KpiStrip />)
    const dashes = screen.getAllByText("—")
    expect(dashes.length).toBeGreaterThanOrEqual(3)
  })

  it("renders numeric KPI values when provided", () => {
    render(<KpiStrip totalIncoherences={7} pendingHitl={2} chainValid={true} />)
    expect(screen.getByText("7")).toBeInTheDocument()
    expect(screen.getByText("2")).toBeInTheDocument()
    expect(screen.getByText("OK")).toBeInTheDocument()
  })

  it("shows ERRORE when chainValid is false", () => {
    render(<KpiStrip totalIncoherences={0} pendingHitl={0} chainValid={false} />)
    expect(screen.getByText("ERRORE")).toBeInTheDocument()
  })
})
