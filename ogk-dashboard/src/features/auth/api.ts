import { ApiError, apiFetch } from '../../shared/api/client.ts'
import type { Account, AdminAccount } from '../../shared/types/auth.ts'

export type Credentials = { email: string; password: string }

export async function getMe(): Promise<Account | null> {
  try {
    return await apiFetch<Account>('/api/auth/me')
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null
    throw error
  }
}

export const login = (body: Credentials) => apiFetch<Account>('/api/auth/login', { method: 'POST', json: body })

export const register = (body: Credentials) =>
  apiFetch<Account>('/api/auth/register', { method: 'POST', json: body })

export const logout = () => apiFetch<void>('/api/auth/logout', { method: 'POST' })

export const listAccounts = (lockedOnly: boolean) =>
  apiFetch<AdminAccount[]>(`/api/admin/accounts?locked=${lockedOnly}`)

export const unlockAccount = (id: number) =>
  apiFetch<AdminAccount>(`/api/admin/accounts/${id}/unlock`, { method: 'POST' })
