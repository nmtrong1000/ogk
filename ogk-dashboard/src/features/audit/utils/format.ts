import type { AuditAction, AuditEntry, AuditValue } from '@/shared/types/audit.ts'
import type { AppGroup, AppRule, AppRuleAction } from '@/shared/types/policy.ts'

const TARGET_LABELS: Record<string, string> = {
  child: 'con',
  device: 'thiết bị',
  windows_account: 'tài khoản Windows',
  policy: 'chính sách',
  child_request: 'yêu cầu',
}

const FIELD_LABELS: Record<string, Record<string, string>> = {
  child: { name: 'Tên', birth_year: 'Năm sinh' },
  device: { name: 'Tên máy' },
  windows_account: { child_id: 'Con được gán (mã số)' },
  child_request: {
    status: 'Trạng thái',
    domain: 'Tên miền',
    message: 'Lời nhắn',
    type: 'Loại yêu cầu',
  },
  policy: {
    policy_version: 'Phiên bản',
    weekday_quota_minutes: 'Giới hạn ngày thường (phút)',
    weekend_quota_minutes: 'Giới hạn cuối tuần (phút)',
    weekly_schedule: 'Lịch cho phép',
    app_rules: 'Luật ứng dụng',
    app_groups: 'Nhóm ứng dụng',
    web_allowlist: 'Tên miền được cho phép',
    web_blocklist: 'Tên miền bị chặn',
    blocked_categories: 'Nhóm website bị chặn',
  },
}

const RULE_ACTIONS: Record<AppRuleAction, string> = { block: 'Chặn', allow: 'Cho phép' }
const SHA_PREFIX = 8
const CATEGORY_LABELS: Record<string, string> = {
  education: 'Giáo dục',
  entertainment: 'Giải trí',
  social: 'Mạng xã hội',
  games: 'Trò chơi',
  adult: 'Không phù hợp lứa tuổi',
  unclassified: 'Chưa phân loại',
}

function formatRule(rule: AppRule): string {
  const hash = rule.sha256 ? ` (SHA-256 ${rule.sha256.slice(0, SHA_PREFIX)}…)` : ''
  return `${RULE_ACTIONS[rule.action] ?? rule.action} ${rule.name}${hash}`
}

function isAppRule(value: unknown): value is AppRule {
  return (
    typeof value === 'object' &&
    value !== null &&
    'name' in value &&
    typeof value.name === 'string' &&
    'action' in value &&
    typeof value.action === 'string'
  )
}

function isAppGroup(value: unknown): value is AppGroup {
  return (
    typeof value === 'object' &&
    value !== null &&
    'name' in value &&
    typeof value.name === 'string' &&
    'budget_minutes' in value &&
    (typeof value.budget_minutes === 'number' || value.budget_minutes === null)
  )
}

const ACTION_VERBS: Record<AuditAction, string> = { create: 'Thêm', update: 'Sửa', delete: 'Xóa' }

const TARGET_VERBS: Record<string, Partial<Record<AuditAction, string>>> = {
  device: { create: 'Ghép đôi', delete: 'Gỡ' },
  windows_account: { update: 'Gán' },
}

export const ACTION_TONES = { create: 'success', update: 'brand', delete: 'danger' } as const

export function targetLabel(type: string): string {
  return TARGET_LABELS[type] ?? type
}

export function actionLabel(entry: Pick<AuditEntry, 'action' | 'target_type'>): string {
  const verb = TARGET_VERBS[entry.target_type]?.[entry.action] ?? ACTION_VERBS[entry.action] ?? entry.action
  return `${verb} ${targetLabel(entry.target_type)}`
}

export function fieldLabel(targetType: string, field: string): string {
  return FIELD_LABELS[targetType]?.[field] ?? field
}

export function formatValue(value: AuditValue[string] | undefined, targetType?: string, field?: string): string {
  if (value === null || value === undefined || value === '') return '(trống)'
  if (typeof value === 'boolean') return value ? 'Có' : 'Không'
  if (Array.isArray(value)) {
    if (value.length === 0) {
      if (field === 'app_rules') return '(không có luật)'
      if (field === 'blocked_categories') return '(không có nhóm bị chặn)'
      return '(không có mục nào)'
    }
    if (value.every((item): item is string => typeof item === 'string')) {
      return value
        .map((item) =>
          targetType === 'policy' && field === 'blocked_categories' ? (CATEGORY_LABELS[item] ?? item) : item,
        )
        .join(', ')
    }
    if (value.every(isAppRule)) return value.map(formatRule).join('; ')
    if (value.every(isAppGroup)) {
      return value
        .map((group) => `${group.name}${group.budget_minutes === null ? '' : ` (${group.budget_minutes} phút/ngày)`}`)
        .join('; ')
    }
    return value
      .map((item) => (typeof item === 'object' && item !== null ? JSON.stringify(item) : String(item)))
      .join('; ')
  }
  if (typeof value === 'object' && value !== null) return JSON.stringify(value)
  return String(value)
}

export type FieldChange = { field: string; label: string; before?: string; after?: string }

export function changes(entry: AuditEntry): FieldChange[] {
  const known = Object.keys(FIELD_LABELS[entry.target_type] ?? {})
  const fields = new Set([...Object.keys(entry.old_value ?? {}), ...Object.keys(entry.new_value ?? {})])
  const ordered = [...known.filter((f) => fields.has(f)), ...[...fields].filter((f) => !known.includes(f))]
  return ordered.map((field) => ({
    field,
    label: fieldLabel(entry.target_type, field),
    before:
      entry.old_value && field in entry.old_value
        ? formatValue(entry.old_value[field], entry.target_type, field)
        : undefined,
    after:
      entry.new_value && field in entry.new_value
        ? formatValue(entry.new_value[field], entry.target_type, field)
        : undefined,
  }))
}
