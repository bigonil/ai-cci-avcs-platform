import { describe, it, expect } from 'vitest'
import { formatEur, formatDate, severityColor } from '@/lib/utils'

describe('formatEur', () => {
  it('formats positive number with EUR suffix', () => {
    expect(formatEur(80000)).toBe('+80.000 €')
  })
  it('formats negative number', () => {
    expect(formatEur(-5000)).toBe('-5.000 €')
  })
  it('formats zero', () => {
    expect(formatEur(0)).toBe('0 €')
  })
})

describe('formatDate', () => {
  it('formats ISO string to locale date', () => {
    const result = formatDate('2026-06-06T10:00:00Z')
    expect(result).toMatch(/2026/)
  })
})

describe('severityColor', () => {
  it('returns red for CRITICAL', () => {
    expect(severityColor('CRITICAL')).toContain('ef4444')
  })
  it('returns orange for HIGH', () => {
    expect(severityColor('HIGH')).toContain('f97316')
  })
  it('returns amber for MEDIUM', () => {
    expect(severityColor('MEDIUM')).toContain('f59e0b')
  })
  it('returns blue for LOW', () => {
    expect(severityColor('LOW')).toContain('818cf8')
  })
})
