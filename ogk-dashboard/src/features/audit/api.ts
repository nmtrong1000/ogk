import { apiFetch } from '../../shared/api/client.ts'
import type { AuditPage } from '../../shared/types/audit.ts'

export const PAGE_SIZE = 20

export const auditKey = (page: number) => ['audit', page] as const

export const listAudit = (page: number, size = PAGE_SIZE) =>
  apiFetch<AuditPage>(`/api/audit?page=${page}&size=${size}`)
