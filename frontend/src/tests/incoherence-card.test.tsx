import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { IncoherenceCard } from '@/components/incoherence-card'
import type { Incoherence } from '@/lib/types'

const mockIncoherence: Incoherence = {
  id: 'abc123',
  domain: 'hera_it',
  rule_id: 'R001',
  severity: 'CRITICAL',
  description: 'Azure commitment supera allocazione CTO',
  detected_at: '2026-06-06T10:00:00Z',
  impact_eur: 80000,
  evidence_chunks: ['hera_azure_1#chunk_3'],
  explanation: null,
  citations: [],
  grounding_verified: null,
}

function renderCard(props?: Partial<typeof mockIncoherence>) {
  return render(
    <MemoryRouter>
      <IncoherenceCard incoherence={{ ...mockIncoherence, ...props }} />
    </MemoryRouter>
  )
}

describe('IncoherenceCard', () => {
  it('renders rule_id in monospace', () => {
    renderCard()
    expect(screen.getByText('R001')).toBeInTheDocument()
  })

  it('renders severity badge', () => {
    renderCard()
    expect(screen.getByText('CRITICAL')).toBeInTheDocument()
  })

  it('renders description', () => {
    renderCard()
    expect(screen.getByText(/Azure commitment/)).toBeInTheDocument()
  })

  it('renders formatted impact', () => {
    renderCard()
    expect(screen.getByText('+80.000 €')).toBeInTheDocument()
  })

  it('renders link to detail page', () => {
    renderCard()
    const link = screen.getByRole('link')
    expect(link).toHaveAttribute('href', '/incoherences/abc123')
  })

  it('renders HIGH severity with orange badge', () => {
    renderCard({ severity: 'HIGH', rule_id: 'R002' })
    expect(screen.getByText('HIGH')).toBeInTheDocument()
  })
})
