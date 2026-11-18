export type Child = {
  id: number
  name: string
  birth_year: number
  created_at: string
  updated_at: string
}

export type ChildInput = {
  name: string
  birth_year: number
}

export type WindowsAccount = {
  id: number
  sid: string
  username: string
  child_id: number | null
}

export type Device = {
  id: number
  name: string
  created_at: string
  last_seen_at: string | null
  accounts: WindowsAccount[]
}
