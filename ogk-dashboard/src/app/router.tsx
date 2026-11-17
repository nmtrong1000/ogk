import { createBrowserRouter, type RouteObject } from 'react-router-dom'
import { AdminAccountsPage, LoginPage, RegisterPage, RequireAuth } from '../features/auth/index.ts'
import HomePage from './HomePage.tsx'
import Layout from './Layout.tsx'

// Trang xem design system chỉ có khi chạy `npm run dev`; bản build bỏ hẳn nhánh này.
const devRoutes: RouteObject[] = import.meta.env.DEV
  ? [{ path: '/design', lazy: async () => ({ Component: (await import('./DesignSystemPage.tsx')).default }) }]
  : []

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/register', element: <RegisterPage /> },
      {
        element: <RequireAuth />,
        children: [{ path: '/', element: <HomePage /> }],
      },
      {
        element: <RequireAuth roles={['admin']} />,
        children: [{ path: '/admin/accounts', element: <AdminAccountsPage /> }],
      },
      ...devRoutes,
    ],
  },
])
