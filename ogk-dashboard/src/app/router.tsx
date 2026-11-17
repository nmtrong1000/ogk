import { createBrowserRouter } from 'react-router-dom'
import HomePage from './HomePage.tsx'
import Layout from './Layout.tsx'

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [{ path: '/', element: <HomePage /> }],
  },
])
