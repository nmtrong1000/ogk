import { Navigate, Outlet, useLocation } from 'react-router-dom'
import type { Role } from '../../shared/types/auth.ts'
import { errorMessage } from './messages.ts'
import { useMe } from './useMe.ts'

type Props = { roles?: Role[] }

/** Chặn route theo phiên và vai trò. Server vẫn tự kiểm tra quyền ở mọi API. */
export default function RequireAuth({ roles }: Props) {
  const me = useMe()
  const location = useLocation()

  if (me.isPending) return <p>Đang tải...</p>
  if (me.isError) return <p className="error">{errorMessage(me.error)}</p>
  if (!me.data) {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?next=${next}`} replace />
  }
  if (roles && !roles.includes(me.data.role)) {
    return (
      <section>
        <h1>Không có quyền</h1>
        <p>Tài khoản của bạn không được mở trang này.</p>
      </section>
    )
  }
  return <Outlet />
}
