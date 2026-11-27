import { expect, test } from '@playwright/test'

test('reports show weekly labels and paginate child requests', async ({ page }) => {
  const requestedPages = new Set<number>()
  const daily = Array.from({ length: 7 }, (_, index) => ({
    date: `2026-11-${String(27 - index).padStart(2, '0')}`,
    seconds: (index + 1) * 1800,
  }))

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
  await page.route('**/api/children/7/reports?*', async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        child_id: 7,
        from: '2026-11-21',
        to: '2026-11-27',
        time_zone: 'Asia/Ho_Chi_Minh',
        daily,
        weekly: [
          { week_start: '2026-11-16', seconds: 21_600 },
          { week_start: '2026-11-23', seconds: 54_000 },
        ],
        total_seconds: 75_600,
        top_apps: [],
        top_domains: [],
        blocked: { apps: 0, domains: 0, total: 0 },
        quota_today_seconds: 7200,
      },
    })
  })
  await page.route('**/api/children/7/reports/requests?*', async (route) => {
    const url = new URL(route.request().url())
    const pageNumber = Number(url.searchParams.get('page'))
    const size = Number(url.searchParams.get('size'))
    requestedPages.add(pageNumber)
    const allItems = Array.from({ length: 15 }, (_, index) => ({
      id: index + 1,
      device_id: 1,
      child_id: 7,
      child_name: 'An',
      type: index % 2 === 0 ? 'add_time' : 'blocked_domain',
      domain: index % 2 === 0 ? null : `site-${index + 1}.example`,
      status: index % 3 === 0 ? 'pending' : index % 3 === 1 ? 'approved' : 'rejected',
      message: null,
      created_at: `2026-11-${String(27 - index).padStart(2, '0')}T08:00:00Z`,
      decided_at: null,
    }))
    const start = (pageNumber - 1) * size
    await route.fulfill({
      status: 200,
      json: { items: allItems.slice(start, start + size), total: allItems.length, page: pageNumber, size },
    })
  })

  await page.goto('/children/7/reports')
  await expect(page.getByRole('heading', { name: 'Báo cáo sử dụng' })).toBeVisible()
  await page.getByRole('button', { name: 'Theo tuần' }).click()
  await expect(page.getByText('Tuần 1')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Trang 2' })).toBeVisible()

  await page.getByRole('button', { name: 'Trang 2' }).click()
  await expect(page.getByText('Báo chặn nhầm: site-12.example')).toBeVisible()
  expect([...requestedPages]).toContain(2)
})
