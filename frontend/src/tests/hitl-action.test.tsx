// frontend/src/tests/hitl-action.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { HitlAction } from '@/pages/hitl-action'
import type { HitlAction as HitlActionType } from '@/lib/types'

vi.mock('@/hooks/use-hitl-queue', () => ({
  useHitlAction: () => ({
    data: {
      id: 'act-001',
      action_type: 'Budget override',
      description: 'Autorizzazione spesa aggiuntiva 80.000 EUR',
      impact: '+80.000 EUR',
      status: 'PENDING',
      created_at: '2026-06-06T10:00:00Z',
      incoherence_id: 'abc123',
    } satisfies HitlActionType,
    isLoading: false,
  }),
  useApproveHitl: () => ({ mutate: vi.fn(), isPending: false }),
  useRejectHitl: () => ({ mutate: vi.fn(), isPending: false }),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => vi.fn() }
})

function renderPage() {
  const qc = new QueryClient()
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/hitl/act-001']}>
        <Routes>
          <Route path="/hitl/:actionId" element={<HitlAction />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('HitlAction', () => {
  it('renders action description', () => {
    renderPage()
    expect(screen.getByText(/Autorizzazione spesa aggiuntiva/)).toBeInTheDocument()
  })

  it('disables approve/reject when motivation is too short', () => {
    renderPage()
    const approveBtn = screen.getByRole('button', { name: /approva/i })
    expect(approveBtn).toBeDisabled()
  })

  it('enables buttons when motivation is long enough', async () => {
    renderPage()
    const textarea = screen.getByRole('textbox')
    await userEvent.type(textarea, 'Motivazione valida con almeno venti caratteri.')
    const approveBtn = screen.getByRole('button', { name: /approva/i })
    expect(approveBtn).not.toBeDisabled()
  })
})
