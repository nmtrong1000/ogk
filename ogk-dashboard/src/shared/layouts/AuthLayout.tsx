import { Outlet } from 'react-router-dom'
import AppFooter from '@/shared/layouts/AppFooter.tsx'

export default function AuthLayout() {
  return (
    <div className="flex min-h-dvh flex-col">
      <main className="grid flex-1 place-items-center px-4 py-8">
        <Outlet />
      </main>
      <AppFooter />
    </div>
  )
}
