import { expect, test } from '@playwright/test'

test('policy overview shows metric cards and opens screen-time settings', async ({ page }) => {
  const weeklySchedule = ['0'.repeat(48), ...Array(6).fill('1'.repeat(48))]
  const policy = {
    child_id: 7,
    policy_version: 3,
    weekday_quota_minutes: 120,
    weekend_quota_minutes: 180,
    weekly_schedule: weeklySchedule,
    app_rules: [
      { name: 'blocked.exe', sha256: null, action: 'block', group_id: 'unclassified' },
      { name: 'allowed.exe', sha256: null, action: 'allow', group_id: 'unclassified' },
    ],
    app_groups: [],
    web_allowlist: [],
    web_blocklist: [],
    blocked_categories: [],
    set_by: 'parent@example.com',
    updated_at: '2026-01-01T00:00:00Z',
  }

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
  await page.route('**/api/children/7/policy', async (route) => {
    await route.fulfill({ status: 200, json: policy })
  })
  await page.route('**/api/children/7/policy/versions', async (route) => {
    await route.fulfill({ status: 200, json: [] })
  })

  await page.goto('/children/7/policy')

  await expect(page.getByRole('heading', { name: 'Chính sách hiện tại' })).toBeVisible()
  await expect(page.getByText('Ngày thường (T2–T6)')).toBeVisible()
  await expect(page.getByText('Cuối tuần (T7, CN)')).toBeVisible()
  await expect(page.getByText('Tổng giờ mở theo lịch')).toBeVisible()
  await expect(page.getByText('1 bị chặn')).toBeVisible()
  await expect(page.getByText('1 cho phép')).toBeVisible()

  await page.getByRole('button', { name: 'Sửa thời gian dùng máy' }).click()
  await expect(page).toHaveURL('/children/7/screentime')
})
