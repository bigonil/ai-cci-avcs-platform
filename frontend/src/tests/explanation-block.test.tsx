import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ExplanationBlock } from '@/components/explanation-block'

describe('ExplanationBlock', () => {
  it('renders text with citation badges', () => {
    render(
      <ExplanationBlock
        explanation="Azure commitment [source: hera_azure_1#chunk_3] supera allocazione."
        citations={['hera_azure_1#chunk_3']}
        groundingVerified={true}
      />
    )
    expect(screen.getByText(/Azure commitment/)).toBeInTheDocument()
    expect(screen.getAllByText('hera_azure_1#chunk_3').length).toBeGreaterThanOrEqual(1)
  })

  it('shows verified badge when grounding is confirmed', () => {
    render(
      <ExplanationBlock
        explanation="Testo [source: chunk_1]."
        citations={['chunk_1']}
        groundingVerified={true}
      />
    )
    expect(screen.getByText(/Grounding verificato/i)).toBeInTheDocument()
  })

  it('renders citations list at the bottom', () => {
    render(
      <ExplanationBlock
        explanation="Testo [source: doc_1#chunk_2]."
        citations={['doc_1#chunk_2']}
        groundingVerified={true}
      />
    )
    expect(screen.getAllByText('doc_1#chunk_2').length).toBeGreaterThanOrEqual(1)
  })
})
