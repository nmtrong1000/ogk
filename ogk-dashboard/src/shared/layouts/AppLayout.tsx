/*
 * Child-view pages get a header without parent navigation and never ask /api/auth/me, so a child's browser never
 * learns whether a parent is signed in on it.
 */
import { useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { LogoutButton, useMe } from '@/features/auth/index.ts'
import AppFooter from '@/shared/layouts/AppFooter.tsx'
import Breadcrumbs from '@/shared/layouts/Breadcrumbs.tsx'
import ChildPageNavigation from '@/shared/layouts/ChildPageNavigation.tsx'
import DashboardSidebar from '@/shared/layouts/DashboardSidebar.tsx'

export default function AppLayout() {
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
      <header className="glass flex w-full items-center px-4 py-3 sm:px-6">
        <Brand />
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 sm:py-10">
        <Breadcrumbs />
        <Outlet />
      </main>
      <AppFooter />
    </div>
  )
}

function ParentLayout() {
  const { data: me } = useMe()
  const [mobileOpen, setMobileOpen] = useState(false)
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-20 w-full px-3 pt-3 sm:px-4">
        <div className="glass flex min-h-16 w-full items-center justify-between gap-4 rounded-glass px-4 py-3 sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              aria-label={mobileOpen ? 'Đóng menu' : 'Mở menu'}
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen((open) => !open)}
              className="glass-input grid size-10 shrink-0 place-items-center rounded-control text-brand-700 lg:hidden"
            >
              {mobileOpen ? (
                <X aria-hidden="true" className="size-5" />
              ) : (
                <Menu aria-hidden="true" className="size-5" />
              )}
            </button>
            <Link to="/" className="no-underline hover:text-ink">
              <Brand />
            </Link>
          </div>
          {me && (
            <div className="flex min-w-0 items-center gap-2 sm:gap-3">
              <span className="hidden max-w-64 truncate text-sm text-ink-muted sm:inline" title={me.email}>
                {me.email}
              </span>
              <LogoutButton />
            </div>
          )}
        </div>
      </header>
      <div className="flex flex-1 gap-3 px-3 pb-3 pt-3 sm:gap-4 sm:px-4 sm:pb-4">
        <aside className="glass sticky top-20 hidden h-[calc(100dvh-9rem)] w-[270px] shrink-0 self-start overflow-y-auto overscroll-contain rounded-glass p-3 lg:block">
          <DashboardSidebar role={me?.role} />
        </aside>
        <main className="min-w-0 flex-1 px-1 py-3 sm:px-2 sm:py-4 lg:px-4">
          <div className="mx-auto w-full max-w-7xl">
            <Breadcrumbs />
            <ChildPageNavigation />
            <Outlet />
          </div>
        </main>
      </div>
      <AppFooter />
      {mobileOpen && (
        <div className="fixed inset-0 z-30 lg:hidden">
          <button
            type="button"
            aria-label="Đóng menu"
            onClick={() => setMobileOpen(false)}
            className="absolute inset-0 bg-ink/25"
          />
          <aside className="glass-strong absolute left-3 top-3 bottom-3 w-[calc(100vw-1.5rem)] max-w-96 overflow-y-auto overscroll-contain rounded-glass p-3 pt-5">
            <div className="mb-2 flex justify-end">
              <button
                type="button"
                aria-label="Đóng menu"
                onClick={() => setMobileOpen(false)}
                className="glass-input grid size-9 place-items-center rounded-control text-brand-700"
              >
                <X aria-hidden="true" className="size-5" />
              </button>
            </div>
            <DashboardSidebar role={me?.role} onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}
    </div>
  )
}
