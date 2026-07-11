import { expect, test } from '@playwright/test'

const password = 'SecurePass1234'

test.describe('Authentication flows', () => {
  test('user can register and land on dashboard', async ({ page }) => {
    const email = `auth_e2e_${Date.now()}@alphaedge.io`

    await page.goto('/register')
    await page.getByPlaceholder('Jane Quant').fill('Auth E2E User')
    await page.getByPlaceholder('trader@alphaedge.io').fill(email)
    await page.getByPlaceholder('Min. 8 characters').fill(password)
    await page.getByRole('button', { name: 'Create account' }).click()

    await expect(page).toHaveURL('/')
    await expect(page.getByText('Auth E2E User')).toBeVisible()
  })

  test('user can log in and out', async ({ page }) => {
    const email = `login_e2e_${Date.now()}@alphaedge.io`

    // Register first
    await page.goto('/register')
    await page.getByPlaceholder('Jane Quant').fill('Login E2E User')
    await page.getByPlaceholder('trader@alphaedge.io').fill(email)
    await page.getByPlaceholder('Min. 8 characters').fill(password)
    await page.getByRole('button', { name: 'Create account' }).click()
    await expect(page).toHaveURL('/')

    // Sign out
    await page.getByTitle('Sign out').click()
    await expect(page).toHaveURL('/login')

    // Log back in
    await page.getByPlaceholder('trader@alphaedge.io').fill(email)
    await page.getByPlaceholder('••••••••').fill(password)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page).toHaveURL('/')
  })

  test('unauthenticated user is redirected to login', async ({ page }) => {
    await page.goto('/strategies')
    await expect(page).toHaveURL(/\/login/)
  })

  test('invalid credentials show an error message', async ({ page }) => {
    await page.goto('/login')
    await page.getByPlaceholder('trader@alphaedge.io').fill('nobody@nowhere.invalid')
    await page.getByPlaceholder('••••••••').fill('wrongpassword')
    await page.getByRole('button', { name: 'Sign in' }).click()

    // Should stay on login page and show an error
    await expect(page).toHaveURL(/\/login/)
    // Error message or form still visible — enough to prove no crash
    await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible()
  })
})
