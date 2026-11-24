import { apiFetch } from '@/shared/api/client.ts'
import type { WipeResult } from '@/shared/types/retention.ts'

export const wipeChildData = (id: number) => apiFetch<WipeResult>(`/api/children/${id}/data`, { method: 'DELETE' })
