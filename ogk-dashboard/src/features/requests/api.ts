import { apiFetch } from '@/shared/api/client.ts'

export type ChildRequest = {
  id: number
  device_id: number
  child_id: number
  child_name: string
  type: 'add_time' | 'blocked_domain'
  domain: string | null
  status: 'pending' | 'approved' | 'rejected'
  message: string | null
  created_at: string
  decided_at: string | null
}

export const requestsKey = ['requests'] as const
export const listRequests = () => apiFetch<ChildRequest[]>('/api/requests')
export const decideRequest = (id: number, approve: boolean, message: string) =>
  apiFetch<ChildRequest>(`/api/requests/${id}/decision`, {
    method: 'POST',
    json: { approve, message: message.trim() || null },
  })
