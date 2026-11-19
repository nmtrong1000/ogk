import { apiFetch } from '@/shared/api/client.ts'
import type { DeviceAlert } from '@/shared/types/alerts.ts'

export const alertsKey = (deviceId: number | null) => ['alerts', deviceId] as const

export const listAlerts = (deviceId: number | null) =>
  apiFetch<DeviceAlert[]>(deviceId === null ? '/api/alerts' : `/api/alerts?device_id=${deviceId}`)
