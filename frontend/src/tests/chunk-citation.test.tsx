import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChunkCitation } from '@/components/chunk-citation'

describe('ChunkCitation', () => {
  it('renders the chunk id text', () => {
    render(<ChunkCitation chunkId="hera_azure_1#chunk_3" />)
    expect(screen.getByText('hera_azure_1#chunk_3')).toBeInTheDocument()
  })

  it('renders as inline badge span', () => {
    const { container } = render(<ChunkCitation chunkId="doc_1#chunk_2" />)
    expect(container.querySelector('span')).not.toBeNull()
  })

  it('uses title attribute equal to chunkId', () => {
    const { container } = render(<ChunkCitation chunkId="test#chunk_0" />)
    const span = container.querySelector('span')
    expect(span?.title).toBe('test#chunk_0')
  })
})
