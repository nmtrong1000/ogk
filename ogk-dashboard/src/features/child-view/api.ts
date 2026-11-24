import { apiFetch } from '@/shared/api/client.ts'
import type { Page, Report, RuleChange } from '@/shared/types/reports.ts'

export const childViewMeKey = ['child-view', 'me'] as const
export const childViewTodayKey = ['child-view', 'today'] as const
export const childViewRuleLogKey = (page: number) => ['child-view', 'rule-log', page] as const

export const openChildView = (code: string) =>
  apiFetch<void>('/api/child-view/session', { method: 'POST', json: { code } })
export const closeChildView = () => apiFetch<void>('/api/child-view/logout', { method: 'POST' })
export const getChildViewMe = () => apiFetch<{ name: string }>('/api/child-view/me')
export const getChildViewToday = () => apiFetch<Report>('/api/child-view/today')
export const getChildViewRuleLog = (page: number, size: number) =>
  apiFetch<Page<RuleChange>>(`/api/child-view/rule-log?page=${page}&size=${size}`)
