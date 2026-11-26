/*
 * 4xx errors are not retried because a retry gives the same answer and keeps the page loading.
 * When the session expires mid-use, cached data is cleared and the user goes to login with the current page as `next`.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router-dom'
import { ApiError, setUnauthorizedHandler } from '@/shared/api/client.ts'
import { ToastProvider } from '@/shared/components/ToastProvider.tsx'
import { switchSession } from '@/features/auth/index.ts'
import { router } from '@/app/router.tsx'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (count, error) => !(error instanceof ApiError && error.status >= 400 && error.status < 500) && count < 2,
    },
  },
})

setUnauthorizedHandler(() => {
  const { pathname, search } = router.state.location
  switchSession(queryClient, null)
  if (pathname !== '/login') {
    router.navigate(`/login?next=${encodeURIComponent(pathname + search)}`, { replace: true })
  }
})

export default function App() {
  return (
    <ToastProvider>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ToastProvider>
  )
}
