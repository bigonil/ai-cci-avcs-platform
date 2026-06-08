// frontend/src/tests/generate-explanation-button.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GenerateExplanationButton } from '@/components/generate-explanation-button'

describe('GenerateExplanationButton', () => {
  it('renders the button text', () => {
    render(<GenerateExplanationButton onGenerate={vi.fn()} isPending={false} />)
    expect(screen.getByRole('button', { name: /genera spiegazione/i })).toBeInTheDocument()
  })

  it('calls onGenerate when clicked', async () => {
    const onGenerate = vi.fn()
    render(<GenerateExplanationButton onGenerate={onGenerate} isPending={false} />)
    await userEvent.click(screen.getByRole('button'))
    expect(onGenerate).toHaveBeenCalledOnce()
  })

  it('disables button and shows loading text when pending', () => {
    render(<GenerateExplanationButton onGenerate={vi.fn()} isPending={true} />)
    const btn = screen.getByRole('button')
    expect(btn).toBeDisabled()
    expect(screen.getByText(/generazione/i)).toBeInTheDocument()
  })
})
