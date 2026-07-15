import { expect, test } from '@playwright/test'

const password = 'SecurePass1234'

test('paper trading smoke: broker, strategy, backtest nav, deploy UI, logout', async ({
  page,
}) => {
  const email = `smoke_${Date.now()}@alphaedge.io`
  const strategyName = `sma-cross-${Date.now()}`
  const portfolioName = `paper-${Date.now()}`

  await page.goto('/register')
  await page.getByPlaceholder('Jane Quant').fill('Smoke Trader')
  await page.getByPlaceholder('trader@alphaedge.io').fill(email)
  await page.getByPlaceholder('Min. 8 characters').fill(password)
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page).toHaveURL('/')
  await expect(page.getByText('Smoke Trader')).toBeVisible()

  // Paper portfolio
  await page.getByRole('link', { name: 'Portfolios' }).click()
  await page.getByRole('button', { name: 'New portfolio' }).click()
  await page.getByPlaceholder('Momentum book').fill(portfolioName)
  await page.locator('form').getByRole('button', { name: 'Create portfolio' }).click()
  await expect(page.getByText(portfolioName)).toBeVisible({ timeout: 15_000 })

  // Paper broker connection
  await page.getByRole('link', { name: 'Orders' }).click()
  await expect(page.getByRole('heading', { name: 'Order blotter' })).toBeVisible()
  const addPaper = page.getByRole('button', { name: /paper/i }).first()
  if (await addPaper.isVisible().catch(() => false)) {
    await addPaper.click()
  }
  // Connection list should render (paper or empty-state CTA)
  await expect(page.getByText(/paper|connection|No connections/i).first()).toBeVisible()

  // Strategy create
  await page.getByRole('link', { name: 'Strategies' }).click()
  await page.getByRole('button', { name: 'New strategy' }).click()
  await page.getByPlaceholder('Golden Cross v1').fill(strategyName)
  await page.locator('form').getByRole('button', { name: 'Create strategy' }).click()
  await expect(page.getByText(strategyName)).toBeVisible({ timeout: 15_000 })
  await page.getByText(strategyName).click()
  await expect(page.getByRole('button', { name: /Validate/i }).first()).toBeVisible()
  await expect(page.getByRole('button', { name: /Deploy to paper/i })).toBeVisible()

  // Critical navigation
  for (const name of ['Backtests', 'Deployments', 'Marketplace', 'Organizations', 'Insights']) {
    await page.getByRole('link', { name }).click()
    await expect(page.locator('h1, h2').first()).toBeVisible()
  }

  // Logout
  await page.getByTitle('Sign out').click()
  await expect(page).toHaveURL('/login')
})
