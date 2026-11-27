import { expect, test, type Page } from '@playwright/test'

const parent = { id: 1, email: 'parent@example.com', role: 'parent' }
const admin = { id: 2, email: 'admin@example.com', role: 'admin' }

async function mockMe(page: Page, user = parent) {
  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({ status: 200, json: user })
  })
}

test('device list and enrollment screens render with mocked API data', async ({ page }) => {
  await mockMe(page)
  await page.route('**/api/devices', async (route) => route.fulfill({ status: 200, json: [] }))
  await page.route('**/api/children', async (route) => route.fulfill({ status: 200, json: [] }))

  await page.goto('/devices')
  await expect(page.getByRole('heading', { name: 'Danh sách thiết bị' })).toBeVisible()
  await expect(page.getByText('Chưa có thiết bị nào.')).toBeVisible()
  await page.goto('/devices/add')
  await expect(page.getByRole('heading', { name: 'Thêm thiết bị' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Quy trình ghép đôi' })).toBeVisible()
})

test('device alerts and child requests show their empty states', async ({ page }) => {
  await mockMe(page)
  await page.route('**/api/alerts?device_id=5', async (route) => route.fulfill({ status: 200, json: [] }))
  await page.route('**/api/requests', async (route) => route.fulfill({ status: 200, json: [] }))

  await page.goto('/devices/5/alerts')
  await expect(page.getByRole('heading', { name: 'Cảnh báo thiết bị' })).toBeVisible()
  await expect(page.getByText('Thiết bị này chưa có cảnh báo nào.')).toBeVisible()
  await page.goto('/children/requests')
  await expect(page.getByRole('heading', { name: 'Yêu cầu của con' })).toBeVisible()
  await expect(page.getByText('Chưa có yêu cầu nào.')).toBeVisible()
})

test('admin account and web filter pages render with mocked catalog data', async ({ page }) => {
  await mockMe(page, admin)
  await page.route('**/api/admin/accounts?locked=*', async (route) => route.fulfill({ status: 200, json: [] }))
  await page.route('**/api/admin/webfilter/catalog', async (route) => route.fulfill({ status: 200, json: [] }))

  await page.goto('/admin/accounts')
  await expect(page.getByRole('heading', { name: 'Tài khoản phụ huynh' })).toBeVisible()
  await expect(page.getByText('Chưa có tài khoản phụ huynh nào.')).toBeVisible()
  await page.goto('/admin/webfilter')
  await expect(page.getByRole('heading', { name: 'Bảng phân loại website' })).toBeVisible()
})

test('audit page loads an empty paginated result', async ({ page }) => {
  await mockMe(page, admin)
  await page.route('**/api/audit?*', async (route) =>
    route.fulfill({ status: 200, json: { items: [], total: 0, page: 1, size: 20 } }),
  )

  await page.goto('/audit')
  await expect(page.getByRole('heading', { name: 'Nhật ký thay đổi' })).toBeVisible()
  await expect(page.getByText('Chưa có thay đổi nào.')).toBeVisible()
})

test('child view routes show clear errors without a one-time session', async ({ page }) => {
  await page.route('**/api/child-view/session', async (route) =>
    route.fulfill({ status: 400, json: { detail: 'invalid_code' } }),
  )
  await page.goto('/child-view/start#code=invalid')
  await expect(page.getByRole('heading', { name: 'Không thể mở báo cáo' })).toBeVisible()
  await expect(page.getByText('Đường dẫn này đã hết hạn.', { exact: false })).toBeVisible()

  await page.route('**/api/child-view/me', async (route) =>
    route.fulfill({ status: 401, json: { detail: 'not_authenticated' } }),
  )
  await page.goto('/child-view/')
  await expect(page.getByRole('heading', { name: 'Không thể mở báo cáo' })).toBeVisible()
  await expect(page.getByText('Đường dẫn này đã hết hạn.', { exact: false })).toBeVisible()
})

test('unknown URLs use the standalone not found layout', async ({ page }) => {
  await mockMe(page)
  await page.goto('/url-khong-ton-tai')

  await expect(page.getByText('404', { exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Không tìm thấy trang' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Về trang chủ' })).toBeVisible()
  await expect(page.getByRole('navigation', { name: 'Menu chính' })).toHaveCount(0)
})
