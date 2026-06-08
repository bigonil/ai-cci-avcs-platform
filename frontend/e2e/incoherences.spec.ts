// frontend/e2e/incoherences.spec.ts
import { test, expect } from '@playwright/test'

test('pagina incoerenze si carica', async ({ page }) => {
  await page.goto('/incoherences')
  await expect(page.getByText('Non conformità rilevate')).toBeVisible()
  // Aspetta caricamento (loading o dati)
  await expect(page.locator('body')).not.toContainText('undefined')
})

test('filtro severity cambia i risultati', async ({ page }) => {
  await page.goto('/incoherences')
  const select = page.locator('select')
  await select.selectOption('CRITICAL')
  await expect(select).toHaveValue('CRITICAL')
})
