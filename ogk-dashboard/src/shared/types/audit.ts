export type AuditAction = 'create' | 'update' | 'delete'

export type AuditValue = Record<string, string | number | boolean | null>

export type AuditEntry = {
  id: number
  at: string
  actor_id: number
  actor_email: string | null
  ip: string
  action: AuditAction
  target_type: string
  target_id: number
  /** null khi tạo (old), khi xóa (new), hoặc khi admin xem. */
  old_value: AuditValue | null
  new_value: AuditValue | null
}

export type AuditPage = {
  items: AuditEntry[]
  total: number
  page: number
  size: number
}
