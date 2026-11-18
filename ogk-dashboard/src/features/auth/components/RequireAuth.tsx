import { Link, Navigate, Outlet, useLocation } from 'react-router-dom'
import { Alert, Card, Spinner } from '../../../shared/components/index.ts'
import type { Role } from '../../../shared/types/auth.ts'
import { errorMessage } from '../utils/messages.ts'
import { useMe } from '../hooks/useMe.ts'

type Props = { roles?: Role[] }

/** Chặn route theo phiên và vai trò. Server vẫn tự kiểm tra quyền ở mọi API. */
export default function RequireAuth({ roles }: Props) {
  const me = useMe()
  const location = useLocation()

  if (me.isPending) {
    return (
      <div className="grid place-items-center py-20">
        <Spinner size="lg" />
      </div>
    )
  }
  if (me.isError) return <Alert tone="error">{errorMessage(me.error)}</Alert>
  if (!me.data) {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?next=${next}`} replace />
  }
  if (roles && !roles.includes(me.data.role)) {
    return (
      <Card strong className="mx-auto max-w-md text-center">
        <h1 className="text-xl font-bold text-ink">Không có quyền</h1>
        <p className="mt-2 text-ink-muted">Tài khoản của bạn không được mở trang này.</p>
        <p className="mt-4">
          <Link to="/">Về trang tổng quan</Link>
        </p>
      </Card>
    )
  }
  return <Outlet />
}
