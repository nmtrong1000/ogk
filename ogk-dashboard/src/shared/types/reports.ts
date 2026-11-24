export type DayUsage = { date: string; seconds: number }
export type WeekUsage = { week_start: string; seconds: number }
export type AppUsage = { name: string; seconds: number }
export type DomainUsage = { domain: string; count: number }

export type Report = {
  child_id: number
  from: string
  to: string
  time_zone: string
  daily: DayUsage[]
  weekly: WeekUsage[]
  total_seconds: number
  top_apps: AppUsage[]
  top_domains: DomainUsage[]
  blocked: { apps: number; domains: number; total: number }
  quota_today_seconds: number
}

export type Page<T> = { items: T[]; total: number; page: number; size: number }

export type ReportRequest = {
  id: number
  device_id: number
  child_id: number
  child_name: string | null
  type: 'add_time' | 'blocked_domain'
  domain: string | null
  status: 'pending' | 'approved' | 'rejected'
  message: string | null
  created_at: string
  decided_at: string | null
}

export type RuleChange = {
  id: number
  at: string
  changes: Record<string, { old: unknown; new: unknown }>
}
