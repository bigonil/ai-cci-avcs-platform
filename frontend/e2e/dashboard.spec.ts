// frontend/e2e/dashboard.spec.ts
import { test, expect } from '@playwright/test'

test('dashboard carica KPI strip', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('Dashboard')).toBeVisible()
  await expect(page.getByText('Incoerenze')).toBeVisible()
  await expect(page.getByText('HITL in attesa')).toBeVisible()
  await expect(page.getByText('Audit chain')).toBeVisible()
})

test('sidebar navigation funziona', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('link', { name: 'Incoerenze' }).click()
  await expect(page).toHaveURL('/incoherences')
  await page.getByRole('link', { name: 'Audit Trail' }).click()
  await expect(page).toHaveURL('/audit')
})
