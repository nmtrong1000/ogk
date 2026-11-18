export type PairingCode = {
  id: number
  code: string
  expires_at: string
  expires_in: number
}

export type PairingCodeStatus = {
  id: number
  status: 'pending' | 'used' | 'expired'
  expires_at: string
  device_id: number | null
}
