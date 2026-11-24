/*
 * The rule log carries raw policy fields as stored in the audit log, so each known field is turned into short
 * sentences here; an unknown field still gets a generic sentence so a new rule type never disappears silently.
 */
import { formatDuration } from '@/shared/utils/duration.ts'

const CATEGORY_NAMES: Record<string, string> = {
  education: 'Giáo dục',
  entertainment: 'Giải trí',
  social: 'Mạng xã hội',
  games: 'Trò chơi',
  adult: 'Không phù hợp lứa tuổi',
  unclassified: 'Chưa phân loại',
}

type AppRule = { name?: string; action?: string }

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === 'string') : []
}

function blockedApps(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value
    .filter((r): r is AppRule => typeof r === 'object' && r !== null)
    .filter((r) => r.action === 'block' && typeof r.name === 'string')
    .map((r) => r.name as string)
}

function added(before: string[], after: string[]) {
  return after.filter((item) => !before.includes(item))
}

function quota(label: string, before: unknown, after: unknown): string[] {
  if (typeof after !== 'number') return []
  const from = typeof before === 'number' ? ` từ ${formatDuration(before * 60)}` : ''
  return [`Thời gian được dùng máy ${label} đổi${from} thành ${formatDuration(after * 60)}.`]
}

export function describeChange(field: string, before: unknown, after: unknown): string[] {
  switch (field) {
    case 'weekday_quota_minutes':
      return quota('ngày thường', before, after)
    case 'weekend_quota_minutes':
      return quota('cuối tuần', before, after)
    case 'weekly_schedule':
      return ['Giờ được dùng máy trong tuần đã thay đổi.']
    case 'app_rules': {
      const was = blockedApps(before)
      const now = blockedApps(after)
      const lines = [
        ...added(was, now).map((name) => `Ứng dụng ${name} bị chặn.`),
        ...added(now, was).map((name) => `Ứng dụng ${name} được dùng lại.`),
      ]
      return lines.length ? lines : ['Danh sách ứng dụng đã thay đổi.']
    }
    case 'web_allowlist': {
      const was = strings(before)
      const now = strings(after)
      return [
        ...added(was, now).map((domain) => `Trang ${domain} được mở cho em.`),
        ...added(now, was).map((domain) => `Trang ${domain} không còn trong danh sách được mở.`),
      ]
    }
    case 'web_blocklist': {
      const was = strings(before)
      const now = strings(after)
      return [
        ...added(was, now).map((domain) => `Trang ${domain} bị chặn.`),
        ...added(now, was).map((domain) => `Trang ${domain} không còn bị chặn.`),
      ]
    }
    case 'blocked_categories': {
      const was = strings(before)
      const now = strings(after)
      const name = (key: string) => CATEGORY_NAMES[key] ?? key
      return [
        ...added(was, now).map((key) => `Nhóm trang "${name(key)}" bị chặn.`),
        ...added(now, was).map((key) => `Nhóm trang "${name(key)}" không còn bị chặn.`),
      ]
    }
    default:
      return ['Bố mẹ đã thay đổi một luật.']
  }
}

export function describeChanges(changes: Record<string, { old: unknown; new: unknown }>): string[] {
  const lines = Object.entries(changes).flatMap(([field, value]) => describeChange(field, value.old, value.new))
  return lines.length ? lines : ['Bố mẹ đã cập nhật luật.']
}
