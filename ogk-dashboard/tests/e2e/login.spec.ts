import { expect, test } from '@playwright/test'

test('login screen loads with mocked unauthenticated session', async ({ page }) => {
  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({ status: 401, json: { detail: 'not_authenticated' } })
  })

  await page.goto('/login')

  await expect(page.getByRole('heading', { name: 'Đăng nhập' })).toBeVisible()
  await expect(page.locator('header')).toHaveCount(0)
  await expect(page.getByRole('contentinfo')).toContainText(`© ${new Date().getFullYear()} by Nguyễn Minh Trọng`)
  await expect(page.getByLabel('Email')).toBeVisible()
  await expect(page.getByText('Email*', { exact: true })).toBeVisible()
  await expect(page.getByText('Mật khẩu*', { exact: true })).toBeVisible()
  await expect(page.getByRole('textbox', { name: 'Mật khẩu', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Đăng ký' })).toBeVisible()

  await page.goto('/register')

  await expect(page.getByRole('heading', { name: 'Tạo tài khoản phụ huynh' })).toBeVisible()
  await expect(page.locator('header')).toHaveCount(0)
  await expect(page.getByRole('contentinfo')).toContainText(`© ${new Date().getFullYear()} by Nguyễn Minh Trọng`)
  await expect(page.getByLabel('Email')).toBeVisible()
  await expect(page.getByText('Email*', { exact: true })).toBeVisible()
  await expect(page.getByText('Mật khẩu*', { exact: true })).toBeVisible()
  await expect(page.getByText('Nhập lại mật khẩu*', { exact: true })).toBeVisible()
  await expect(page.getByRole('textbox', { name: 'Mật khẩu', exact: true })).toBeVisible()
  await expect(page.getByLabel('Nhập lại mật khẩu')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Đăng nhập' })).toBeVisible()

  await page.getByLabel('Email').fill('parent@example.com')
  await page.getByRole('textbox', { name: 'Mật khẩu', exact: true }).fill('short')
  await page.getByLabel('Nhập lại mật khẩu').fill('short')
  await page.getByRole('button', { name: 'Tạo tài khoản' }).click()
  await expect(page.getByRole('alert')).toContainText('Mật khẩu phải có ít nhất 10 ký tự')
  await page.getByRole('button', { name: 'Đóng thông báo' }).click()
  await expect(page.getByRole('alert')).toHaveCount(0)
})

test('each failed login attempt shows its own toast', async ({ page }) => {
  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({ status: 401, json: { detail: 'not_authenticated' } })
  })
  await page.route('**/api/health', async (route) => {
    await route.fulfill({ status: 200, json: { status: 'ok' } })
  })
  await page.route('**/api/auth/login', async (route) => {
    await route.fulfill({ status: 401, json: { detail: 'invalid_credentials' } })
  })

  await page.goto('/login')
  await page.getByLabel('Email').fill('parent@example.com')
  await page.getByRole('textbox', { name: 'Mật khẩu', exact: true }).fill('wrong-password')

  const submit = page.getByRole('button', { name: 'Đăng nhập' })
  await submit.click()
  await expect(page.getByRole('alert')).toHaveCount(1)
  await expect(page.getByRole('alert').first()).toContainText('Email hoặc mật khẩu không đúng')
  await expect(page.getByRole('alert').first()).toHaveCSS('border-width', '0px')
  await expect(page.locator('.toast-progress, .toast-rail')).toHaveCount(0)

  await submit.click()
  await expect(page.getByRole('alert')).toHaveCount(2)
})

test('login validates required fields before sending a request', async ({ page }) => {
  let loginRequests = 0
  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({ status: 401, json: { detail: 'not_authenticated' } })
  })
  await page.route('**/api/auth/login', async (route) => {
    loginRequests += 1
    await route.fulfill({ status: 401, json: { detail: 'invalid_credentials' } })
  })

  await page.goto('/login')
  await page.getByRole('button', { name: 'Đăng nhập' }).click()
  await expect(page.getByRole('alert').first()).toContainText('Vui lòng nhập email')

  await page.getByLabel('Email').fill('parent@example.com')
  await page.getByRole('button', { name: 'Đăng nhập' }).click()
  await expect(page.getByRole('alert').last()).toContainText('Vui lòng nhập mật khẩu')
  expect(loginRequests).toBe(0)

  await page.getByRole('textbox', { name: 'Mật khẩu', exact: true }).fill('secret')
  await page.getByLabel('Email').fill('invalid-email')
  await page.getByRole('button', { name: 'Đăng nhập' }).click()
  await expect(page.getByRole('alert').last()).toContainText('Email không hợp lệ')
  expect(loginRequests).toBe(0)
})
