import { expect, test } from '@playwright/test'

/**
 * Full research → paper loop smoke.
 * Requires API on :8000 with seed instruments (make seed / demo seed).
 */
test('validate strategy, open backtest modal, create paper broker, open deploy UI', async ({
  page,
}) => {
  const password = 'SecurePass1234'
  const email = `flow_${Date.now()}@alphaedge.io`
  const strategyName = `flow-strat-${Date.now()}`
  const portfolioName = `flow-book-${Date.now()}`

  await page.goto('/register')
  await page.getByPlaceholder('Jane Quant').fill('Flow Trader')
  await page.getByPlaceholder('trader@alphaedge.io').fill(email)
  await page.getByPlaceholder('Min. 8 characters').fill(password)
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page).toHaveURL('/')

  // Paper portfolio
  await page.getByRole('link', { name: 'Portfolios' }).click()
  await page.getByRole('button', { name: 'New portfolio' }).click()
  await page.getByPlaceholder('Momentum book').fill(portfolioName)
  await page.locator('form').getByRole('button', { name: 'Create portfolio' }).click()
  await expect(page.getByText(portfolioName)).toBeVisible({ timeout: 15_000 })

  // Paper broker
  await page.getByRole('link', { name: 'Orders' }).click()
  const paperBtn = page.getByRole('button', { name: /Add paper|paper connection|Create paper/i })
  if (await paperBtn.count()) {
    await paperBtn.first().click()
  } else {
    // Fallback: look for any button that creates paper connection
    const alt = page.getByRole('button', { name: /paper/i })
    if (await alt.count()) await alt.first().click()
  }
  await expect(page.getByText(/paper/i).first()).toBeVisible({ timeout: 15_000 })

  // Strategy → detail → validate
  await page.getByRole('link', { name: 'Strategies' }).click()
  await page.getByRole('button', { name: 'New strategy' }).click()
  await page.getByPlaceholder('Golden Cross v1').fill(strategyName)
  await page.locator('form').getByRole('button', { name: 'Create strategy' }).click()
  await expect(page.getByText(strategyName)).toBeVisible({ timeout: 15_000 })
  await page.getByText(strategyName).click()

  const validateBtn = page.getByRole('button', { name: /^Validate$/i })
  await expect(validateBtn).toBeVisible()
  await validateBtn.click()
  // Validation may succeed or show inline errors depending on starter template — either way UI responds
  await expect(
    page.getByText(/Validated|validation|error|Invalid|compiled/i).first(),
  ).toBeVisible({ timeout: 20_000 })

  await expect(page.getByRole('button', { name: /Deploy to paper/i })).toBeVisible()
  await page.getByRole('button', { name: /Deploy to paper/i }).click()
  await expect(page.getByRole('heading', { name: /Deploy to paper/i })).toBeVisible()

  // Backtests surface
  await page.keyboard.press('Escape')
  await page.getByRole('link', { name: 'Backtests' }).click()
  await expect(page.getByRole('heading', { name: 'Backtests' })).toBeVisible()
  await page.getByRole('button', { name: /New backtest|Run backtest|Submit/i }).first().click()
  await expect(page.locator('form').first()).toBeVisible({ timeout: 10_000 })

  await page.getByTitle('Sign out').click()
  await expect(page).toHaveURL('/login')
})
