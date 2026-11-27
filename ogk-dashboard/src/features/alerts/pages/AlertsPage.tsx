/*
 * Alerts arrive with the agent's 60-second heartbeat, so the list refetches on the same cadence.
 */
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { Alert, Card, EmptyState, Spinner } from '@/shared/components/index.ts'
import { alertsKey, listAlerts } from '@/features/alerts/api.ts'
import DeviceAlertList from '@/features/alerts/components/DeviceAlertList.tsx'
import { alertErrorMessage } from '@/features/alerts/utils/messages.ts'

const REFRESH_MS = 60_000

export default function AlertsPage() {
  const rawId = useParams().id
  const deviceId = rawId && /^\d+$/.test(rawId) ? Number(rawId) : null
  const alerts = useQuery({
    queryKey: alertsKey(deviceId),
    queryFn: () => {
      if (deviceId === null) throw new Error('Mã thiết bị không hợp lệ.')
      return listAlerts(deviceId)
    },
    enabled: deviceId !== null,
    refetchInterval: REFRESH_MS,
  })

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Cảnh báo thiết bị</h1>
        <p className="mt-1 text-ink-muted">Khi máy của con bị tắt cưỡng chế hoặc bị chỉnh đồng hồ.</p>
      </div>

      {deviceId === null && <Alert tone="error">Mã thiết bị không hợp lệ.</Alert>}
      {alerts.isError && <Alert tone="error">{alertErrorMessage(alerts.error)}</Alert>}
      {deviceId !== null && alerts.isPending && (
        <div className="grid place-items-center py-12">
          <Spinner />
        </div>
      )}
      {alerts.data?.length === 0 && (
        <Card>
          <EmptyState message="Thiết bị này chưa có cảnh báo nào." />
        </Card>
      )}
      {alerts.data && alerts.data.length > 0 && (
        <DeviceAlertList deviceName={alerts.data[0].device_name} alerts={alerts.data} />
      )}
    </div>
  )
}
