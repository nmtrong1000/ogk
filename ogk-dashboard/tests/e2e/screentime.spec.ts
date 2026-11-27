import { expect, test } from '@playwright/test'

test('screen-time page creates and confirms removal of groups before saving their budgets', async ({ page }) => {
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

  await page.goto('/children/7/screentime')

  await expect(page.getByRole('heading', { name: 'Thời gian dùng máy', level: 1 })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Ngân sách theo nhóm ứng dụng' })).toBeVisible()
  await expect(page.getByText('0 ứng dụng').first()).toBeVisible()

  await page.getByRole('button', { name: 'Tạo nhóm' }).click()
  const createDialog = page.getByRole('dialog', { name: 'Tạo nhóm ứng dụng' })
  await createDialog.getByLabel('Tên nhóm').fill('Nhóm thử')
  await createDialog.getByLabel('Ngân sách mỗi ngày').fill('35')
  await createDialog.getByRole('button', { name: 'Tạo nhóm' }).click()
  const customGroup = page.locator('article').filter({ hasText: 'Nhóm thử' })
  await expect(customGroup).toBeVisible()
  await expect(customGroup.getByLabel('Ngân sách mỗi ngày')).toHaveValue('35')

  await page.getByRole('button', { name: 'Xóa nhóm Nhóm thử' }).click()
  const deleteDialog = page.getByRole('dialog', { name: 'Xóa nhóm Nhóm thử?' })
  await expect(deleteDialog).toBeVisible()
  await deleteDialog.getByRole('button', { name: 'Xóa nhóm' }).click()
  await expect(customGroup).toHaveCount(0)

  const educationGroup = page.locator('article').filter({ hasText: 'Học tập' })
  await educationGroup.getByLabel('Ngân sách mỗi ngày').fill('45')
  await page.getByRole('button', { name: 'Lưu nhóm và ngân sách' }).click()
  await expect(page.getByText('Đã lưu nhóm và ngân sách ứng dụng.')).toBeVisible()
  expect(policyBody).toMatchObject({
    app_groups: expect.arrayContaining([expect.objectContaining({ id: 'education', budget_minutes: 45 })]),
  })
})
