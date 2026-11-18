import { apiFetch } from '../../shared/api/client.ts'
import type { Child, ChildInput } from '../../shared/types/family.ts'

export const childrenKey = ['children'] as const
export const childKey = (id: number) => ['children', id] as const

export const listChildren = () => apiFetch<Child[]>('/api/children')

export const getChild = (id: number) => apiFetch<Child>(`/api/children/${id}`)

export const createChild = (body: ChildInput) => apiFetch<Child>('/api/children', { method: 'POST', json: body })

export const updateChild = (id: number, body: Partial<ChildInput>) =>
  apiFetch<Child>(`/api/children/${id}`, { method: 'PATCH', json: body })

export const deleteChild = (id: number) => apiFetch<void>(`/api/children/${id}`, { method: 'DELETE' })
