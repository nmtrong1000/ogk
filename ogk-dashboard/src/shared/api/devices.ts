/*
 * Device calls used by both enrollment (assign right after pairing) and family (manage devices).
 * Features cannot import each other, so they share these through shared/.
 */
import { apiFetch } from '@/shared/api/client.ts'
import type { Device, WindowsAccount } from '@/shared/types/family.ts'

export const devicesKey = ['devices'] as const
export const childDevicesKey = (childId: number) => ['devices', 'child', childId] as const

export const listDevices = () => apiFetch<Device[]>('/api/devices')

export const listChildDevices = (childId: number) => apiFetch<Device[]>(`/api/children/${childId}/devices`)

export const assignAccount = (deviceId: number, accountId: number, childId: number | null) =>
  apiFetch<WindowsAccount>(`/api/devices/${deviceId}/accounts/${accountId}`, {
    method: 'PUT',
    json: { child_id: childId },
  })

export const removeDevice = (deviceId: number) => apiFetch<void>(`/api/devices/${deviceId}`, { method: 'DELETE' })
