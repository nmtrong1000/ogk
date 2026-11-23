import { apiFetch } from '@/shared/api/client.ts'

export type CommandType = 'lock' | 'unlock' | 'add_time'

export type ParentCommand = {
  id: number
  child_id: number
  type: CommandType
  minutes: number
  status: 'pending' | 'acknowledged'
  created_at: string
  acknowledged_at: string | null
}

export const commandsKey = (deviceId: number, childId: number) => ['commands', deviceId, childId] as const

export const listCommands = (deviceId: number, childId: number) =>
  apiFetch<ParentCommand[]>(`/api/devices/${deviceId}/children/${childId}/commands`)

export const sendCommand = (deviceId: number, childId: number, type: CommandType) =>
  apiFetch<ParentCommand>(`/api/devices/${deviceId}/children/${childId}/commands`, {
    method: 'POST',
    json: { type },
  })
