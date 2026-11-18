import { apiFetch } from '@/shared/api/client.ts'
import type { PairingCode, PairingCodeStatus } from '@/shared/types/enrollment.ts'
import type { Child } from '@/shared/types/family.ts'

export const childrenKey = ['children'] as const
export const pairingCodeKey = (id: number) => ['pairing-codes', id] as const

export const listChildren = () => apiFetch<Child[]>('/api/children')

export const createPairingCode = () =>
  apiFetch<PairingCode>('/api/pairing-codes', { method: 'POST', json: { consent: true } })

export const getPairingCodeStatus = (id: number) => apiFetch<PairingCodeStatus>(`/api/pairing-codes/${id}`)
