import { useQuery, type QueryClient } from '@tanstack/react-query'
import type { Account } from '../../../shared/types/auth.ts'
import { getMe } from '../api.ts'

export const ME_KEY = ['me'] as const

export function useMe() {
  return useQuery({ queryKey: ME_KEY, queryFn: getMe, staleTime: 60_000 })
}

/**
 * Đổi phiên (đăng nhập, đăng xuất, hết phiên): cập nhật `me` tại chỗ và bỏ dữ liệu của phiên cũ.
 * Không dùng queryClient.clear() vì nó xóa luôn query `me`, khiến component đang theo dõi
 * (header) giữ giá trị cũ.
 */
export function switchSession(queryClient: QueryClient, account: Account | null) {
  queryClient.setQueryData(ME_KEY, account)
  queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== ME_KEY[0] })
}
