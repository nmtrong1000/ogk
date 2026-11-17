import { createBrowserRouter } from 'react-router-dom'
import { AdminAccountsPage, LoginPage, RegisterPage, RequireAuth } from '../features/auth/index.ts'
import HomePage from './HomePage.tsx'
import Layout from './Layout.tsx'

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
    ],
  },
])
