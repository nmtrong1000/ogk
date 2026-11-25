export type AppRuleAction = 'allow' | 'block'

export type AppRule = {
  name: string
  sha256: string | null
  action: AppRuleAction
  group_id: string
}

export type AppGroup = { id: string; name: string; budget_minutes: number | null }

export type PolicyRules = {
  weekday_quota_minutes: number
  weekend_quota_minutes: number
  weekly_schedule: string[]
  app_rules: AppRule[]
  app_groups: AppGroup[]
  web_allowlist: string[]
  web_blocklist: string[]
  blocked_categories: string[]
}

export type Policy = PolicyRules & {
  child_id: number
  policy_version: number
  set_by: string | null
  updated_at: string
}

export type PolicyVersion = PolicyRules & {
  policy_version: number
  set_by: string | null
  created_at: string
}

export type PolicyUpdate = Partial<PolicyRules>
