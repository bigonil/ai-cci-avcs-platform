// frontend/src/lib/utils.ts
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import type { Severity } from './types'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

export function formatEur(amount: number): string {
  if (amount === 0) return '0 €'
  const abs = Math.abs(amount).toLocaleString('it-IT', { useGrouping: true })
  return amount > 0 ? `+${abs} €` : `-${abs} €`
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('it-IT', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

export const SEVERITY_CONFIG: Record<Severity, { color: string; barColor: string; label: string }> = {
  CRITICAL: { color: '#ef4444', barColor: '#ef4444', label: 'CRITICAL' },
  HIGH:     { color: '#f97316', barColor: '#f97316', label: 'HIGH' },
  MEDIUM:   { color: '#f59e0b', barColor: '#f59e0b', label: 'MEDIUM' },
  LOW:      { color: '#818cf8', barColor: '#818cf8', label: 'LOW' },
}

export function severityColor(severity: Severity): string {
  return SEVERITY_CONFIG[severity]!.color
}
