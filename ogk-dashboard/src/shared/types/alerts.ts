export type DeviceAlertType = 'enforcement_disabled' | 'clock_tampered'

export type DeviceAlert = {
  id: number
  device_id: number
  device_name: string
  type: DeviceAlertType
  detail: string | null
  first_seen_at: string
  last_seen_at: string
  resolved_at: string | null
}
