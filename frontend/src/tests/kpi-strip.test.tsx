import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { KpiStrip } from '@/components/kpi-strip'

describe('KpiStrip', () => {
  it('renders incoherence count', () => {
    render(<KpiStrip incoherences={4} hitlPending={2} auditOk={true} loading={false} />)
    expect(screen.getByText('4')).toBeInTheDocument()
    expect(screen.getByText('Incoerenze')).toBeInTheDocument()
  })

  it('renders hitl pending count', () => {
    render(<KpiStrip incoherences={4} hitlPending={2} auditOk={true} loading={false} />)
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('HITL in attesa')).toBeInTheDocument()
  })

  it('shows OK when audit chain is valid', () => {
    render(<KpiStrip incoherences={4} hitlPending={2} auditOk={true} loading={false} />)
    expect(screen.getByText('✓ OK')).toBeInTheDocument()
  })

  it('shows skeleton placeholders when loading', () => {
    const { container } = render(<KpiStrip incoherences={0} hitlPending={0} auditOk={true} loading={true} />)
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0)
  })
})
