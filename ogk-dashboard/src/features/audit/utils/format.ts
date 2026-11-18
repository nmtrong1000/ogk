import type { AuditAction, AuditEntry, AuditValue } from '@/shared/types/audit.ts'

const TARGET_LABELS: Record<string, string> = { child: 'con' }

const FIELD_LABELS: Record<string, Record<string, string>> = {
  child: { name: 'Tên', birth_year: 'Năm sinh' },
}

const ACTION_VERBS: Record<AuditAction, string> = { create: 'Thêm', update: 'Sửa', delete: 'Xóa' }

export const ACTION_TONES = { create: 'success', update: 'brand', delete: 'danger' } as const

export function targetLabel(type: string): string {
  return TARGET_LABELS[type] ?? type
}

export function actionLabel(entry: Pick<AuditEntry, 'action' | 'target_type'>): string {
  return `${ACTION_VERBS[entry.action] ?? entry.action} ${targetLabel(entry.target_type)}`
}

export function fieldLabel(targetType: string, field: string): string {
  return FIELD_LABELS[targetType]?.[field] ?? field
}

export function formatValue(value: AuditValue[string] | undefined): string {
  if (value === null || value === undefined || value === '') return '(trống)'
  if (typeof value === 'boolean') return value ? 'Có' : 'Không'
  return String(value)
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('vi-VN')
}

export type FieldChange = { field: string; label: string; before?: string; after?: string }

export function changes(entry: AuditEntry): FieldChange[] {
  const known = Object.keys(FIELD_LABELS[entry.target_type] ?? {})
  const fields = new Set([...Object.keys(entry.old_value ?? {}), ...Object.keys(entry.new_value ?? {})])
  const ordered = [...known.filter((f) => fields.has(f)), ...[...fields].filter((f) => !known.includes(f))]
  return ordered.map((field) => ({
    field,
    label: fieldLabel(entry.target_type, field),
    before: entry.old_value && field in entry.old_value ? formatValue(entry.old_value[field]) : undefined,
    after: entry.new_value && field in entry.new_value ? formatValue(entry.new_value[field]) : undefined,
  }))
}
