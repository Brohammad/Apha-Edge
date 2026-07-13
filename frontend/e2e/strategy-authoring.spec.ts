import { expect, test } from '@playwright/test'

const password = 'SecurePass1234'

async function registerAndLogin(page: Parameters<Parameters<typeof test>[1]>[0]) {
  const email = `strat_e2e_${Date.now()}@alphaedge.io`
  await page.goto('/register')
  await page.getByPlaceholder('Jane Quant').fill('Strategy E2E Author')
  await page.getByPlaceholder('trader@alphaedge.io').fill(email)
  await page.getByPlaceholder('Min. 8 characters').fill(password)
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page).toHaveURL('/')
}

test.describe('Strategy authoring', () => {
  test('user can create a new strategy', async ({ page }) => {
    await registerAndLogin(page)

    const strategyName = `e2e-strategy-${Date.now()}`
    await page.getByRole('link', { name: 'Strategies' }).click()
    await expect(page.getByRole('heading', { name: 'Strategies' })).toBeVisible()

    await page.getByRole('button', { name: 'New strategy' }).click()
    await page.getByPlaceholder('Golden Cross v1').fill(strategyName)
    await page.locator('form').getByRole('button', { name: 'Create strategy' }).click()

    await expect(page.getByText(strategyName)).toBeVisible({ timeout: 10_000 })
  })

  test('strategies list page loads for authenticated user', async ({ page }) => {
    await registerAndLogin(page)
    await page.goto('/strategies')

    await expect(page.getByRole('heading', { name: 'Strategies' })).toBeVisible()
    await expect(page.locator('body')).not.toContainText('Error')
  })

  test('strategy detail page is navigable', async ({ page }) => {
    await registerAndLogin(page)

    const strategyName = `detail-e2e-${Date.now()}`
    await page.goto('/strategies')
    await page.getByRole('button', { name: 'New strategy' }).click()
    await page.getByPlaceholder('Golden Cross v1').fill(strategyName)
    await page.locator('form').getByRole('button', { name: 'Create strategy' }).click()
    await expect(page.getByText(strategyName)).toBeVisible({ timeout: 10_000 })

    // Click into the strategy detail
    await page.getByText(strategyName).click()
    // Should navigate to a detail page — URL changes
    await expect(page).not.toHaveURL('/strategies')
  })
})
