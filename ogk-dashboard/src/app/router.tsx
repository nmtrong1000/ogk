import { createBrowserRouter, type RouteObject } from 'react-router-dom'
import { AuditPage } from '@/features/audit/index.ts'
import { AdminAccountsPage, LoginPage, RegisterPage, RequireAuth } from '@/features/auth/index.ts'
import { ChildDetailPage, ChildrenPage } from '@/features/family/index.ts'
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
