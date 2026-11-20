import type { AppRule } from '@/shared/types/policy.ts'

export type AuditAction = 'create' | 'update' | 'delete'

export type AuditValue = Record<string, string | number | boolean | null | AppRule[]>

export type AuditEntry = {
  id: number
  at: string
  actor_id: number
  actor_email: string | null
  ip: string
  action: AuditAction
  target_type: string
  target_id: number
  old_value: AuditValue | null
  new_value: AuditValue | null
}

export type AuditPage = {
  items: AuditEntry[]
  total: number
  page: number
  size: number
}
