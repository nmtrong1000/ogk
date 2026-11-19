export type PolicyRules = {
  weekday_quota_minutes: number
  weekend_quota_minutes: number
  weekly_schedule: string[]
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
