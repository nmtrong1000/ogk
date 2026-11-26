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
    if (route.request().method() === 'DELETE') {
      const id = Number(new URL(route.request().url()).pathname.split('/').at(-1))
      children = children.filter((child) => child.id !== id)
      await route.fulfill({ status: 204 })
      return
    }
    await route.continue()
  })

  await page.goto('/children')

  await expect(page.getByRole('navigation', { name: 'Đường dẫn' })).toContainText('Các con')
  await expect(page.getByRole('link', { name: 'An', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Bình', exact: true })).toBeVisible()
  await expect(page.getByText('Tên con*', { exact: true })).toBeVisible()
  await expect(page.getByText('Năm sinh*', { exact: true })).toBeVisible()

  await page.getByRole('button', { name: 'Thêm' }).click()
  await expect(page.getByText('Tên con dài từ 1 đến 64 ký tự')).toBeVisible()
  expect(createBody).toBeUndefined()

  await page.getByLabel('Tên con').fill('Mai')
  await page.getByLabel('Năm sinh').selectOption('2017')
  await page.getByRole('button', { name: 'Thêm' }).click()
  await expect(page.getByText('Đã thêm Mai.')).toBeVisible()
  expect(createBody).toEqual({ name: 'Mai', birth_year: 2017 })
  await expect(page.getByRole('link', { name: 'Mai', exact: true })).toBeVisible()

  const anRow = page.getByRole('row').filter({ hasText: 'An' })
  await anRow.getByRole('button', { name: 'Xóa' }).click()
  const confirmation = page.getByRole('group', { name: 'Xác nhận xóa An' })
  await confirmation.getByRole('button', { name: 'Xóa' }).click()
  await expect(page.getByRole('link', { name: 'An', exact: true })).toHaveCount(0)
})
