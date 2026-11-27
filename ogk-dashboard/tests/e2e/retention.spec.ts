import { expect, test } from '@playwright/test'

test('child data deletion requires confirmation and reports success', async ({ page }) => {
  let deleteRequests = 0

  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({ status: 200, json: { id: 1, email: 'parent@example.com', role: 'parent' } })
  })
  await page.route('**/api/children/7', async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        id: 7,
        name: 'An',
        birth_year: 2015,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    })
  })
  await page.route('**/api/children/7/data', async (route) => {
    if (route.request().method() === 'DELETE') {
      deleteRequests += 1
      await route.fulfill({ status: 200, json: { devices_notified: 0 } })
      return
    }
    await route.fallback()
  })

  await page.goto('/children/7/data')
  await expect(page.getByRole('heading', { name: 'Dữ liệu của con' })).toBeVisible()
  await page.getByRole('button', { name: 'Xóa toàn bộ dữ liệu của con tôi' }).click()

  const confirmation = page.getByRole('dialog', { name: 'Xóa toàn bộ dữ liệu của An?' })
  await expect(confirmation).toBeVisible()
  await confirmation.getByRole('button', { name: 'Hủy' }).click()
  await expect(confirmation).not.toBeVisible()
  expect(deleteRequests).toBe(0)

  await page.getByRole('button', { name: 'Xóa toàn bộ dữ liệu của con tôi' }).click()
  await page.getByRole('dialog', { name: 'Xóa toàn bộ dữ liệu của An?' }).getByRole('button', { name: 'Xóa' }).click()
  await expect(page.getByText('Đã xóa dữ liệu trên máy chủ. Con chưa được gán vào máy tính nào.')).toBeVisible()
  expect(deleteRequests).toBe(1)
})
