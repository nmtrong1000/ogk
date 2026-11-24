import { apiFetch } from '@/shared/api/client.ts'
import type { Page, Report, ReportRequest } from '@/shared/types/reports.ts'

export const reportKey = (id: number, days: number) => ['reports', id, days] as const
export const reportRequestsKey = (id: number, page: number) => ['reports', id, 'requests', page] as const

export const getReport = (id: number, days: number) => apiFetch<Report>(`/api/children/${id}/reports?days=${days}`)

export const getReportRequests = (id: number, page: number, size: number) =>
  apiFetch<Page<ReportRequest>>(`/api/children/${id}/reports/requests?page=${page}&size=${size}`)
