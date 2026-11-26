import { expect, test } from '@playwright/test'

test('dashboard shows the parent overview and server health', async ({ page }) => {
  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({ status: 200, json: { id: 1, email: 'parent@example.com', role: 'parent' } })
  })
  await page.route('**/api/health', async (route) => {
    await route.fulfill({ status: 200, json: { status: 'ok', db: 'ok' } })
  })

  await page.goto('/')

  await expect(page.getByRole('navigation', { name: 'Đường dẫn' })).toContainText('Trang chủ')
  await expect(page.getByRole('heading', { name: 'Tổng quan' })).toBeVisible()
  await page.getByRole('button', { name: 'Gia đình' }).click()
  await expect(page.getByRole('link', { name: 'Các con', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Thiết bị' }).click()
  await expect(page.getByRole('link', { name: 'Danh sách thiết bị', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Thêm thiết bị', exact: true })).toBeVisible()
  await expect(page.getByText('Kết nối tới OGK-Server', { exact: true })).toBeVisible()
  await expect(page.getByText('ok', { exact: true })).toBeVisible()
  await expect(page.getByRole('contentinfo')).toContainText(`© ${new Date().getFullYear()} by Nguyễn Minh Trọng`)
})

test('mobile dashboard opens the sidebar tree from the header', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 })
  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({ status: 200, json: { id: 1, email: 'parent@example.com', role: 'parent' } })
  })
  await page.route('**/api/health', async (route) => {
    await route.fulfill({ status: 200, json: { status: 'ok', db: 'ok' } })
  })

  await page.goto('/')
  await page.getByRole('button', { name: 'Mở menu' }).click()
  const drawer = page.getByRole('complementary')
  await expect(drawer).toBeVisible()
  const drawerBox = await drawer.boundingBox()
  expect(drawerBox!.x).toBe(12)
  expect(drawerBox!.x + drawerBox!.width).toBeGreaterThanOrEqual(362)
  expect(drawerBox!.y + drawerBox!.height).toBeLessThanOrEqual(800)
  await expect(page.getByRole('contentinfo')).toHaveCSS('position', 'static')
  await page.getByRole('button', { name: 'Thiết bị' }).click()
  await expect(page.getByRole('link', { name: 'Thêm thiết bị', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Gia đình' }).click()
  await expect(page.getByRole('link', { name: 'Các con', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Đóng menu' }).last().click()
  await expect(drawer).toBeHidden()
})

test('device submenu highlights only the exact active route', async ({ page }) => {
  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({ status: 200, json: { id: 1, email: 'parent@example.com', role: 'parent' } })
  })

  await page.goto('/devices/add')

  const breadcrumbs = page.getByRole('navigation', { name: 'Đường dẫn' })
  await expect(breadcrumbs.getByRole('link', { name: 'Tổng quan' })).toBeVisible()
  await expect(breadcrumbs.getByRole('link', { name: 'Thiết bị' })).toBeVisible()
  await expect(breadcrumbs.getByText('Thêm thiết bị', { exact: true })).toHaveAttribute('aria-current', 'page')
  const deviceList = page.getByRole('link', { name: 'Danh sách thiết bị', exact: true })
  const addDevice = page.getByRole('link', { name: 'Thêm thiết bị', exact: true })
  await expect(deviceList).toBeVisible()
  await expect(addDevice).toBeVisible()
  await expect(deviceList).not.toHaveAttribute('aria-current', 'page')
  await expect(addDevice).toHaveAttribute('aria-current', 'page')
})

test('desktop dashboard adapts across wide viewports without horizontal overflow', async ({ page }) => {
  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({ status: 200, json: { id: 1, email: 'parent@example.com', role: 'parent' } })
  })
  await page.route('**/api/health', async (route) => {
    await route.fulfill({ status: 200, json: { status: 'ok', db: 'ok' } })
  })
  await page.goto('/')

  for (const width of [1024, 1280, 1440, 1920]) {
    await page.setViewportSize({ width, height: 900 })
    const dimensions = await page.evaluate(() => ({
      viewport: window.innerWidth,
      document: document.documentElement.scrollWidth,
      sidebar: document.querySelector('aside')!.getBoundingClientRect().toJSON(),
      footer: document.querySelector('footer')!.getBoundingClientRect().toJSON(),
      sidebarDisplay: getComputedStyle(document.querySelector('aside')!).display,
    }))

    expect(dimensions.document).toBeLessThanOrEqual(dimensions.viewport)
    expect(dimensions.sidebarDisplay).toBe('block')
    expect(dimensions.sidebar.bottom).toBeLessThan(dimensions.footer.top)
  }
})
