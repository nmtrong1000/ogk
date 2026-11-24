/*
 * Child-view pages get a header without parent navigation and never ask /api/auth/me, so a child's browser never
 * learns whether a parent is signed in on it.
 */
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { LogoutButton, useMe } from '@/features/auth/index.ts'
import { cn } from '@/shared/utils/cn.ts'

function navClass({ isActive }: { isActive: boolean }) {
  return cn(
    'rounded-full px-3 py-1.5 text-sm font-medium no-underline transition',
    isActive ? 'bg-white/80 text-brand-700 shadow-sm' : 'text-ink-muted hover:bg-white/50 hover:text-brand-700',
  )
}

export default function Layout() {
  const { pathname } = useLocation()
  return pathname === '/child-view' || pathname.startsWith('/child-view/') ? <ChildLayout /> : <ParentLayout />
}

function Brand() {
  return (
    <span className="flex items-center gap-2.5 text-ink">
      <span
        aria-hidden
        className="grid size-9 place-items-center rounded-xl bg-linear-to-br from-brand-400 to-brand-600 text-sm font-bold text-white shadow-control"
      >
        O
      </span>
      <span className="text-lg font-bold tracking-tight">OGK</span>
    </span>
  )
}

function ChildLayout() {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="px-3 pt-3 sm:px-4">
        <div className="glass mx-auto flex max-w-5xl items-center rounded-glass px-4 py-2.5">
          <Brand />
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 sm:py-10">
        <Outlet />
      </main>
    </div>
  )
}

function ParentLayout() {
  const { data: me } = useMe()
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-10 px-3 pt-3 sm:px-4">
        <div className="glass mx-auto flex max-w-5xl flex-wrap items-center gap-x-4 gap-y-2 rounded-glass px-4 py-2.5">
          <Link to="/" className="no-underline hover:text-ink">
            <Brand />
          </Link>
          {me && (
            <>
              <nav className="flex items-center gap-1">
                <NavLink to="/" end className={navClass}>
                  Tổng quan
                </NavLink>
                {me.role === 'parent' && (
                  <>
                    <NavLink to="/children" className={navClass}>
                      Các con
                    </NavLink>
                    <NavLink to="/devices" className={navClass}>
                      Thiết bị
                    </NavLink>
                    <NavLink to="/alerts" className={navClass}>
                      Cảnh báo
                    </NavLink>
                    <NavLink to="/requests" className={navClass}>
                      Yêu cầu
                    </NavLink>
                  </>
                )}
                {me.role === 'admin' && (
                  <>
                    <NavLink to="/admin/accounts" className={navClass}>
                      Tài khoản
                    </NavLink>
                    <NavLink to="/admin/webfilter" className={navClass}>
                      Phân loại web
                    </NavLink>
                  </>
                )}
                <NavLink to="/audit" className={navClass}>
                  Nhật ký
                </NavLink>
              </nav>
              <div className="ml-auto flex min-w-0 items-center gap-2">
                <span className="hidden truncate text-sm text-ink-muted sm:inline" title={me.email}>
                  {me.email}
                </span>
                <LogoutButton />
              </div>
            </>
          )}
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 sm:py-10">
        <Outlet />
      </main>
    </div>
  )
}
