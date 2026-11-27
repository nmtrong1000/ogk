import { expect, test } from '@playwright/test'

test('app rules can be created and removed after confirming', async ({ page }) => {
  let policyBody: unknown
  let policy = {
    child_id: 7,
    policy_version: 3,
    weekday_quota_minutes: 120,
    weekend_quota_minutes: 180,
    weekly_schedule: Array(7).fill('1'.repeat(48)),
    app_rules: [],
    app_groups: [
      { id: 'education', name: 'Học tập', budget_minutes: null },
      { id: 'entertainment', name: 'Giải trí', budget_minutes: null },
      { id: 'social', name: 'Mạng xã hội', budget_minutes: null },
      { id: 'games', name: 'Trò chơi', budget_minutes: null },
      { id: 'adult', name: 'Người lớn', budget_minutes: null },
      { id: 'unclassified', name: 'Chưa phân loại', budget_minutes: null },
    ],
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
  await page.route('**/api/children/7/policy/versions', async (route) => {
    await route.fulfill({ status: 200, json: [] })
  })
  await page.route('**/api/children/7/policy', async (route) => {
    if (route.request().method() === 'PATCH') {
      policyBody = route.request().postDataJSON()
      policy = { ...policy, ...(policyBody as Partial<typeof policy>), policy_version: policy.policy_version + 1 }
    }
    await route.fulfill({ status: 200, json: policy })
  })

  await page.goto('/children/7/apps')

  await expect(page.getByRole('heading', { name: 'Thông tin ứng dụng' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Cách áp dụng' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Tạo nhóm ứng dụng' })).toHaveAttribute('href', '/children/7/screentime')

  await page.getByLabel('Tên tệp chạy').fill('demo.exe')
  await page.getByLabel('Nhóm ứng dụng').selectOption('education')
  await page.getByRole('button', { name: 'Thêm luật' }).click()
  await expect(page.getByRole('heading', { name: 'demo.exe' })).toBeVisible()
  expect(policyBody).toMatchObject({
    app_rules: [expect.objectContaining({ name: 'demo.exe', action: 'block', group_id: 'education' })],
  })

  const ruleCard = page.locator('article').filter({ has: page.getByRole('heading', { name: 'demo.exe' }) })
  await ruleCard.getByRole('button', { name: 'Xóa' }).click()
  const confirmation = page.getByRole('dialog', { name: 'Xóa luật cho demo.exe?' })
  await expect(confirmation).toBeVisible()
  await confirmation.getByRole('button', { name: 'Hủy' }).click()
  await expect(ruleCard).toBeVisible()

  await ruleCard.getByRole('button', { name: 'Xóa' }).click()
  await page.getByRole('dialog', { name: 'Xóa luật cho demo.exe?' }).getByRole('button', { name: 'Xóa luật' }).click()
  await expect(page.getByText('Chưa có luật ứng dụng')).toBeVisible()
  expect(policyBody).toMatchObject({ app_rules: [] })
})
