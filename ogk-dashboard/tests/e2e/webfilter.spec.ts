import { expect, test } from '@playwright/test'

test('web filter domains can be added, edited, and moved between lists', async ({ page }) => {
  let policyBody: Record<string, unknown> | undefined
  let policy = {
    child_id: 7,
    policy_version: 3,
    weekday_quota_minutes: 120,
    weekend_quota_minutes: 180,
    weekly_schedule: Array(7).fill('1'.repeat(48)),
    app_rules: [],
    app_groups: [],
    web_allowlist: ['allowed.example'],
    web_blocklist: ['blocked.example'],
    blocked_categories: ['adult'],
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
      policyBody = route.request().postDataJSON() as Record<string, unknown>
      policy = { ...policy, ...policyBody, policy_version: policy.policy_version + 1 }
    }
    await route.fulfill({ status: 200, json: policy })
  })

  await page.goto('/children/7/webfilter')
  await expect(page.getByRole('heading', { name: 'Nhóm bị chặn' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Danh sách chặn' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Danh sách cho phép' })).toBeVisible()

  await page.getByRole('button', { name: 'Thêm tên miền vào danh sách chặn' }).click()
  await page.getByRole('textbox', { name: 'Tên miền' }).fill('new.example')
  await page.getByRole('button', { name: 'Lưu tên miền' }).click()
  await expect(page.getByRole('button', { name: 'new.example', exact: true })).toBeVisible()
  expect(policyBody).toMatchObject({ web_blocklist: ['blocked.example', 'new.example'] })

  await page.getByRole('button', { name: 'Sửa new.example' }).click()
  await page.getByRole('textbox', { name: 'Tên miền' }).fill('edited.example')
  await page.getByRole('button', { name: 'Lưu tên miền' }).click()
  await expect(page.getByRole('button', { name: 'edited.example', exact: true })).toBeVisible()

  await page.getByRole('button', { name: 'edited.example', exact: true }).click()
  await page.getByRole('button', { name: 'Cho phép', exact: true }).click()
  await expect(page.getByRole('button', { name: 'edited.example', exact: true })).toBeVisible()
  expect(policyBody).toMatchObject({
    web_blocklist: ['blocked.example'],
    web_allowlist: ['allowed.example', 'edited.example'],
  })
})
