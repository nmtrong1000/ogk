import { createBrowserRouter, type RouteObject } from 'react-router-dom'
import { AdminAccountsPage, LoginPage, RegisterPage, RequireAuth } from '../features/auth/index.ts'
import { ChildDetailPage, ChildrenPage } from '../features/family/index.ts'
import ErrorPage from './ErrorPage.tsx'
import HomePage from './HomePage.tsx'
import Layout from './Layout.tsx'
import NotFoundPage from './NotFoundPage.tsx'

// Trang xem design system chỉ có khi chạy `npm run dev`; bản build bỏ hẳn nhánh này.
const devRoutes: RouteObject[] = import.meta.env.DEV
  ? [{ path: '/design', lazy: async () => ({ Component: (await import('./DesignSystemPage.tsx')).default }) }]
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
      ...devRoutes,
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
