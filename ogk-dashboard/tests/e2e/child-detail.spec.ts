import { expect, test } from '@playwright/test'

test('child detail is read-only and shows linked devices and commands', async ({ page }) => {
  let commandBody: unknown
  let commandListRequests = 0
  let commands: Array<{
    id: number
    child_id: number
    type: 'lock' | 'unlock' | 'add_time'
    minutes: number
    status: 'pending' | 'acknowledged'
    created_at: string
    acknowledged_at: string | null
  }> = []

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
  await page.route('**/api/children/7/devices', async (route) => {
    await route.fulfill({
      status: 200,
      json: [
        {
          id: 5,
          name: 'OGK-LAPTOP',
          created_at: '2026-01-01T00:00:00Z',
          last_seen_at: null,
          accounts: [{ id: 8, sid: 'S-1-5-21', username: 'An', child_id: 7 }],
        },
      ],
    })
  })
  await page.route('**/api/devices/5/children/7/commands', async (route) => {
    if (route.request().method() === 'GET') {
      commandListRequests += 1
      await route.fulfill({ status: 200, json: commands })
      return
    }

    commandBody = route.request().postDataJSON()
    commands = [
      {
        id: 9,
        child_id: 7,
        ...(commandBody as { type: 'lock' | 'unlock' | 'add_time' }),
        minutes: 0,
        status: 'pending',
        created_at: '2026-01-01T00:00:00Z',
        acknowledged_at: null,
      },
    ]
    await route.fulfill({ status: 201, json: commands[0] })
  })

  await page.goto('/children/7')

  await expect(page.getByRole('navigation', { name: 'Đường dẫn' })).toContainText('Trẻ 7')
  await expect(page.getByRole('heading', { name: 'An', level: 1 })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Sửa thông tin' })).toHaveCount(0)
  await expect(page.getByLabel('Tên con')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Lưu' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Xóa' })).toHaveCount(0)
  await expect(
    page.getByRole('navigation', { name: 'Menu chính' }).getByRole('button', { name: 'Cấu hình trẻ' }),
  ).toHaveCount(0)
  await expect(page.getByRole('navigation', { name: 'Trang của trẻ' }).getByRole('link')).toHaveCount(6)
  await expect(page.getByText('OGK-LAPTOP')).toBeVisible()
  await expect(page.locator('ul').getByText('An', { exact: true })).toBeVisible()
  await expect.poll(() => commandListRequests).toBe(1)
  await page.waitForTimeout(1700)
  expect(commandListRequests).toBe(1)

  await page.getByRole('button', { name: 'Khóa ngay' }).click()
  await expect(page.getByText(/Lệnh gần nhất: Khóa ngay · Đang chờ máy xác nhận/)).toBeVisible()
  expect(commandBody).toEqual({ type: 'lock' })
})
