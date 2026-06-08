// frontend/src/tests/sidebar.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { Sidebar } from '@/components/sidebar'

function renderSidebar() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Sidebar />
    </MemoryRouter>
  )
}

describe('Sidebar', () => {
  it('renders the CCI/AVCS logo text', () => {
    renderSidebar()
    expect(screen.getByText('CCI / AVCS')).toBeInTheDocument()
  })

  it('renders all 4 nav items', () => {
    renderSidebar()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Incoerenze')).toBeInTheDocument()
    expect(screen.getByText('Coda HITL')).toBeInTheDocument()
    expect(screen.getByText('Audit Trail')).toBeInTheDocument()
  })

  it('shows sistema operativo status', () => {
    renderSidebar()
    expect(screen.getByText('Sistema operativo')).toBeInTheDocument()
  })
})
