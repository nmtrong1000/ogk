import { expect, test } from '@playwright/test'

test('children page validates, creates and deletes children', async ({ page }) => {
  let children = [
    { id: 1, name: 'An', birth_year: 2015, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' },
    { id: 2, name: 'Bình', birth_year: 2018, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' },
  ]
  let createBody: unknown

  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({ status: 200, json: { id: 1, email: 'parent@example.com', role: 'parent' } })
  })
  await page.route('**/api/children', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, json: children })
      return
    }

    createBody = route.request().postDataJSON()
    const child = {
      id: 3,
      ...(createBody as { name: string; birth_year: number }),
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    }
    children = [...children, child]
    await route.fulfill({ status: 201, json: child })
  })
  await page.route('**/api/children/*', async (route) => {
    const path = new URL(route.request().url()).pathname
    const segments = path.split('/').filter(Boolean)
    const id = Number(segments[2])

    if (segments[3] === 'devices') {
      await route.fulfill({ status: 200, json: [] })
      return
    }
    if (route.request().method() === 'GET') {
      const child = children.find((item) => item.id === id)
      await route.fulfill(child ? { status: 200, json: child } : { status: 404, json: { detail: 'Not found' } })
      return
    }
    if (route.request().method() === 'DELETE') {
      children = children.filter((child) => child.id !== id)
      await route.fulfill({ status: 204 })
      return
    }
    await route.continue()
  })

  await page.goto('/children')

  await expect(page.getByRole('navigation', { name: 'Đường dẫn' })).toContainText('Các con')
  const anRow = page.getByRole('row', { name: 'Mở chi tiết An' })
  const binhRow = page.getByRole('row', { name: 'Mở chi tiết Bình' })
  await expect(anRow).toBeVisible()
  await expect(binhRow).toBeVisible()
  await expect(anRow.getByRole('button')).toHaveCount(1)
  await expect(anRow.getByRole('button', { name: 'Xóa' })).toBeVisible()

  await expect(page.getByRole('dialog')).toHaveCount(0)
  await page.getByRole('button', { name: 'Thêm trẻ' }).first().click()
  const addDialog = page.getByRole('dialog', { name: 'Thêm trẻ' })
  await expect(addDialog).toBeVisible()
  await expect(page.getByText('Tên con*', { exact: true })).toBeVisible()
  await expect(page.getByText('Năm sinh*', { exact: true })).toBeVisible()

  await page.getByRole('button', { name: 'Thêm trẻ' }).last().click()
  await expect(addDialog.getByRole('alert')).toContainText('Tên con dài từ 1 đến 64 ký tự')
  await expect(page.locator('[aria-label="Thông báo"] [role="alert"]')).toHaveCount(0)

  await page.getByLabel('Tên con').fill('Mai')
  await page.getByRole('button', { name: 'Thêm trẻ' }).last().click()
  await expect(addDialog.getByRole('alert')).toContainText('Chọn năm sinh từ 2000 đến năm nay')
  expect(createBody).toBeUndefined()

  await page.getByLabel('Năm sinh').selectOption('2017')
  await page.getByRole('button', { name: 'Thêm trẻ' }).last().click()
  await expect(page.getByText('Đã thêm Mai.')).toBeVisible()
  await expect(page.getByRole('dialog', { name: 'Thêm trẻ' })).toHaveCount(0)
  expect(createBody).toEqual({ name: 'Mai', birth_year: 2017 })
  await expect(page.getByRole('row', { name: 'Mở chi tiết Mai' })).toBeVisible()

  await anRow.getByRole('button', { name: 'Xóa' }).click()
  const confirmation = page.getByRole('dialog', { name: 'Xóa An?' })
  await expect(confirmation).toBeVisible()
  await expect(page).toHaveURL(/\/children$/)
  await confirmation.getByRole('button', { name: 'Hủy' }).click()
  await expect(confirmation).toHaveCount(0)

  await anRow.getByRole('button', { name: 'Xóa' }).click()
  await page.getByRole('dialog', { name: 'Xóa An?' }).getByRole('button', { name: 'Xóa' }).click()
  await expect(page.getByRole('row', { name: 'Mở chi tiết An' })).toHaveCount(0)

  await binhRow.click()
  await expect(page).toHaveURL(/\/children\/2$/)
})
