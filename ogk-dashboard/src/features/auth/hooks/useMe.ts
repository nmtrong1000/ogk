/*
 * Current account query and session switching.
 * On login, logout or session expiry, `me` is updated in place and the old session's data is removed.
 * queryClient.clear() is not used because it also drops the `me` query, leaving subscribed components
 * (the header) with the stale value.
 */
import { useQuery, type QueryClient } from '@tanstack/react-query'
import type { Account } from '@/shared/types/auth.ts'
import { getMe } from '@/features/auth/api.ts'

export const ME_KEY = ['me'] as const

export function useMe() {
  return useQuery({ queryKey: ME_KEY, queryFn: getMe, staleTime: 60_000 })
}

export function switchSession(queryClient: QueryClient, account: Account | null) {
  queryClient.setQueryData(ME_KEY, account)
  queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== ME_KEY[0] })
}
