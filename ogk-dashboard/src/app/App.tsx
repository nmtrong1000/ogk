import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router-dom'
import { ApiError, setUnauthorizedHandler } from '../shared/api/client.ts'
import { switchSession } from '../features/auth/index.ts'
import { router } from './router.tsx'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Lỗi 4xx thử lại cũng không khác, trả lỗi ngay để trang không treo ở trạng thái tải.
      retry: (count, error) => !(error instanceof ApiError && error.status >= 400 && error.status < 500) && count < 2,
    },
  },
})

// Hết phiên giữa chừng: xóa dữ liệu đã tải rồi về trang đăng nhập, giữ lại trang đang mở.
setUnauthorizedHandler(() => {
  const { pathname, search } = router.state.location
  switchSession(queryClient, null)
  if (pathname !== '/login') {
    router.navigate(`/login?next=${encodeURIComponent(pathname + search)}`, { replace: true })
  }
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
}
