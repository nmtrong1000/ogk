import { apiFetch } from '@/shared/api/client.ts'
import type { Policy, PolicyUpdate } from '@/shared/types/policy.ts'

export const WEB_CATEGORIES = ['education', 'entertainment', 'social', 'games', 'adult', 'unclassified'] as const
export type WebCategory = (typeof WEB_CATEGORIES)[number]
export type CatalogEntry = { domain: string; category: WebCategory; updated_at: string }

export const updateWebPolicy = (childId: number, body: PolicyUpdate) =>
  apiFetch<Policy>(`/api/children/${childId}/policy`, { method: 'PATCH', json: body })

export const getCatalog = () => apiFetch<CatalogEntry[]>('/api/admin/webfilter/catalog')

export const updateCatalog = (domain: string, category: WebCategory | null) =>
  apiFetch<CatalogEntry | null>(`/api/admin/webfilter/catalog/${encodeURIComponent(domain)}`, {
    method: 'PUT',
    json: { category },
  })
