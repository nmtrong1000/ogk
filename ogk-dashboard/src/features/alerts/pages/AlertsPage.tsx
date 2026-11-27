/*
 * Alerts arrive with the agent's 60-second heartbeat, so the list refetches on the same cadence.
 */
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { devicesKey, listDevices } from '@/shared/api/devices.ts'
import { Alert, Card, EmptyState, Select, Spinner } from '@/shared/components/index.ts'
import type { DeviceAlert } from '@/shared/types/alerts.ts'
import { alertsKey, listAlerts } from '@/features/alerts/api.ts'
import DeviceAlertList from '@/features/alerts/components/DeviceAlertList.tsx'
import { alertErrorMessage } from '@/features/alerts/utils/messages.ts'

const REFRESH_MS = 60_000

function parseDevice(value: string | null): number | null {
  if (!value || !/^\d+$/.test(value)) return null
  return Number(value)
}

function groupByDevice(alerts: DeviceAlert[]): { deviceId: number; deviceName: string; alerts: DeviceAlert[] }[] {
  const groups = new Map<number, { deviceId: number; deviceName: string; alerts: DeviceAlert[] }>()
  for (const alert of alerts) {
    const group = groups.get(alert.device_id) ?? {
      deviceId: alert.device_id,
      deviceName: alert.device_name,
      alerts: [],
    }
    group.alerts.push(alert)
    groups.set(alert.device_id, group)
  }
  return [...groups.values()]
}

export default function AlertsPage() {
  const [params, setParams] = useSearchParams()
  const deviceId = parseDevice(params.get('device'))
  const devices = useQuery({ queryKey: devicesKey, queryFn: listDevices })
  const alerts = useQuery({
    queryKey: alertsKey(deviceId),
    queryFn: () => listAlerts(deviceId),
    refetchInterval: REFRESH_MS,
  })

  const options = [
    { value: '', label: 'Tất cả thiết bị' },
    ...(devices.data ?? []).map((d) => ({ value: String(d.id), label: d.name })),
  ]
  const groups = alerts.data ? groupByDevice(alerts.data) : []

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Cảnh báo thiết bị</h1>
        <p className="mt-1 text-ink-muted">Khi máy của con bị tắt cưỡng chế hoặc bị chỉnh đồng hồ.</p>
      </div>

      <Select
        label="Thiết bị"
        className="max-w-xs"
        options={options}
        value={deviceId === null ? '' : String(deviceId)}
        onChange={(e) => setParams(e.target.value ? { device: e.target.value } : {})}
      />

      {alerts.isError && <Alert tone="error">{alertErrorMessage(alerts.error)}</Alert>}
      {alerts.isPending && (
        <div className="grid place-items-center py-12">
          <Spinner />
        </div>
      )}
      {alerts.data?.length === 0 && (
        <Card>
          <EmptyState message="Chưa có cảnh báo nào." />
        </Card>
      )}
      {groups.map((group) => (
        <DeviceAlertList key={group.deviceId} deviceName={group.deviceName} alerts={group.alerts} />
      ))}
    </div>
  )
}
