import { expect, test } from '@playwright/test'

const password = 'SecurePass1234'

test('user can register, explore the app, and sign out', async ({ page }) => {
  const email = `ui_e2e_${Date.now()}@alphaedge.io`
  const strategyName = `golden-cross-${Date.now()}`
  const portfolioName = `paper-book-${Date.now()}`

  // Register
  await page.goto('/register')
  await page.getByPlaceholder('Jane Quant').fill('UI E2E Trader')
  await page.getByPlaceholder('trader@alphaedge.io').fill(email)
  await page.getByPlaceholder('Min. 8 characters').fill(password)
  await page.getByRole('button', { name: 'Create account' }).click()

  // Dashboard
  await expect(page).toHaveURL('/')
  await expect(page.getByText('Markets await, UI.')).toBeVisible()
  await expect(page.getByText('UI E2E Trader')).toBeVisible()

  // Strategies — create one
  await page.getByRole('link', { name: 'Strategies' }).click()
  await expect(page.getByRole('heading', { name: 'Strategies' })).toBeVisible()
  await page.getByRole('button', { name: 'New strategy' }).click()
  await page.getByPlaceholder('Golden Cross v1').fill(strategyName)
  await page.locator('form').getByRole('button', { name: 'Create strategy' }).click()
  await expect(page.getByText(strategyName)).toBeVisible({ timeout: 10_000 })

  // Portfolios — create paper portfolio
  await page.getByRole('link', { name: 'Portfolios' }).click()
  await expect(page.getByRole('heading', { name: 'Portfolios' })).toBeVisible()
  await page.getByRole('button', { name: 'New portfolio' }).click()
  await page.getByPlaceholder('Momentum book').fill(portfolioName)
  await page.locator('form').getByRole('button', { name: 'Create portfolio' }).click()
  await expect(page.getByText(portfolioName)).toBeVisible({ timeout: 10_000 })

  // Browse other sections
  await page.getByRole('link', { name: 'Backtests' }).click()
  await expect(page.getByRole('heading', { name: 'Backtests' })).toBeVisible()

  await page.getByRole('link', { name: 'Marketplace' }).click()
  await expect(page.getByRole('heading', { name: 'Strategy marketplace' })).toBeVisible()

  await page.getByRole('link', { name: 'Organizations' }).click()
  await expect(page.getByRole('heading', { name: 'Organizations' })).toBeVisible()

  await page.getByRole('link', { name: 'Orders' }).click()
  await expect(page.getByRole('heading', { name: 'Order blotter' })).toBeVisible()

  // Sign out and confirm redirect to login
  await page.getByTitle('Sign out').click()
  await expect(page).toHaveURL('/login')
  await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible()

  // Sign back in
  await page.getByPlaceholder('trader@alphaedge.io').fill(email)
  await page.getByPlaceholder('••••••••').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL('/')
  await expect(page.getByText('UI E2E Trader')).toBeVisible()
})
