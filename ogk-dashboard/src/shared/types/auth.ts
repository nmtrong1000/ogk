export type Role = 'parent' | 'admin'

export type Account = {
  id: number
  email: string
  role: Role
}

export type AdminAccount = {
  id: number
  email: string
  failed_attempts: number
  locked_until: string | null
}
