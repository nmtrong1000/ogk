import { createBrowserRouter, type RouteObject } from 'react-router-dom'
import { AlertsPage } from '@/features/alerts/index.ts'
import { AuditPage } from '@/features/audit/index.ts'
import { AdminAccountsPage, LoginPage, RegisterPage, RequireAuth } from '@/features/auth/index.ts'
import { AddDevicePage } from '@/features/enrollment/index.ts'
import { ChildDetailPage, ChildrenPage, DevicesPage } from '@/features/family/index.ts'
import { PolicyPage } from '@/features/policy/index.ts'
import { ScreenTimePage } from '@/features/screentime/index.ts'
import { AppControlPage } from '@/features/appcontrol/index.ts'
import ErrorPage from '@/app/ErrorPage.tsx'
import HomePage from '@/app/HomePage.tsx'
import Layout from '@/app/Layout.tsx'
import NotFoundPage from '@/app/NotFoundPage.tsx'

const devRoutes: RouteObject[] = import.meta.env.DEV
  ? [{ path: '/design', lazy: async () => ({ Component: (await import('@/app/DesignSystemPage.tsx')).default }) }]
  : []

export const router = createBrowserRouter([
  {
    element: <Layout />,
    errorElement: <ErrorPage />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/register', element: <RegisterPage /> },
      {
        element: <RequireAuth />,
        children: [{ path: '/', element: <HomePage /> }],
      },
      {
        element: <RequireAuth roles={['parent']} />,
        children: [
          { path: '/children', element: <ChildrenPage /> },
          { path: '/children/:id', element: <ChildDetailPage /> },
          { path: '/children/:id/policy', element: <PolicyPage /> },
          { path: '/children/:id/screentime', element: <ScreenTimePage /> },
          { path: '/children/:id/apps', element: <AppControlPage /> },
          { path: '/devices', element: <DevicesPage /> },
          { path: '/devices/add', element: <AddDevicePage /> },
          { path: '/alerts', element: <AlertsPage /> },
        ],
      },
      {
        element: <RequireAuth roles={['admin']} />,
        children: [{ path: '/admin/accounts', element: <AdminAccountsPage /> }],
      },
      {
        element: <RequireAuth roles={['parent', 'admin']} />,
        children: [{ path: '/audit', element: <AuditPage /> }],
      },
      ...devRoutes,
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
