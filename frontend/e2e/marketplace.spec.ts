import { expect, test } from '@playwright/test'

const password = 'SecurePass1234'

async function registerAndLogin(page: Parameters<Parameters<typeof test>[1]>[0]) {
  const email = `market_e2e_${Date.now()}@alphaedge.io`
  await page.goto('/register')
  await page.getByPlaceholder('Jane Quant').fill('Marketplace E2E User')
  await page.getByPlaceholder('trader@alphaedge.io').fill(email)
  await page.getByPlaceholder('Min. 8 characters').fill(password)
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page).toHaveURL('/')
}

test.describe('Marketplace navigation', () => {
  test('authenticated user can navigate to marketplace', async ({ page }) => {
    await registerAndLogin(page)

    await page.getByRole('link', { name: 'Marketplace' }).click()
    await expect(page.getByRole('heading', { name: 'Strategy marketplace' })).toBeVisible()
  })

  test('marketplace page loads without errors', async ({ page }) => {
    await registerAndLogin(page)
    await page.goto('/marketplace')

    await expect(page.getByRole('heading', { name: 'Strategy marketplace' })).toBeVisible()
    // Page renders and lists strategies (may be empty)
    await expect(page.locator('body')).not.toContainText('Error')
  })
})
