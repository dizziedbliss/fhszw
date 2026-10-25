import { expect, test } from '@playwright/test'

// Live Elexon data end to end: January is history, so these numbers are fixed.

test('the decision screen works end to end', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Friday 16 January' })).toBeVisible()
  await expect(page.getByText(/of wind forecast across the day/)).toContainText('191,402')

  await page
    .getByRole('group', { name: 'Show tomorrow as' })
    .getByRole('button', { name: 'Table' })
    .click()
  await expect(
    page.getByRole('table', { name: 'Tomorrow, hour by hour' }).locator('tbody tr'),
  ).toHaveCount(24)

  await page.getByRole('combobox', { name: 'Today' }).selectOption({ label: 'Wed 14 Jan' })
  await expect(page).toHaveURL(/today=2026-01-14/)
  await expect(page.getByRole('heading', { name: 'Thursday 15 January' })).toBeVisible()
})

test('the API answers through /api and can reach Elexon', async ({ request }) => {
  const health = await request.get('/api/health')

  expect(health.status()).toBe(200)
  expect(await health.json()).toMatchObject({ status: 'ok', elexon: 'up' })
})
