/*
 * The reload link is a plain <a> so the whole app reloads and leaves the error state.
 */
import { isRouteErrorResponse, useRouteError } from 'react-router-dom'
import { Card } from '../shared/components/index.ts'
import NotFoundPage from './NotFoundPage.tsx'

export default function ErrorPage() {
  const error = useRouteError()
  if (isRouteErrorResponse(error) && error.status === 404) {
    return (
      <main className="px-4 py-10 sm:py-16">
        <NotFoundPage />
      </main>
    )
  }
  if (import.meta.env.DEV) console.error(error)
  return (
    <main className="px-4 py-10 sm:py-16">
      <Card strong className="mx-auto max-w-md text-center">
        <h1 className="text-xl font-bold text-ink">Có lỗi xảy ra</h1>
        <p className="mt-2 text-ink-muted">Trang gặp lỗi không mong muốn. Hãy tải lại trang.</p>
        <p className="mt-5">
          <a href="/">Về trang tổng quan</a>
        </p>
      </Card>
    </main>
  )
}
