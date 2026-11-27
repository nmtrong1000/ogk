/*
 * Alerts arrive with the agent's 60-second heartbeat, so the list refetches on the same cadence.
 */
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { Activity, CircleCheck, ShieldAlert } from 'lucide-react'
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
  const activeCount = alerts.data?.filter((alert) => alert.resolved_at === null).length ?? 0
  const resolvedCount = alerts.data ? alerts.data.length - activeCount : 0

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Cảnh báo thiết bị</h1>
        <p className="mt-1 text-ink-muted">Theo dõi tình trạng bảo vệ và các thay đổi bất thường trên máy.</p>
      </div>

      {deviceId === null && <Alert tone="error">Mã thiết bị không hợp lệ.</Alert>}
      {alerts.isError && <Alert tone="error">{alertErrorMessage(alerts.error)}</Alert>}
      {deviceId !== null && alerts.isPending && (
        <div className="grid place-items-center py-12">
          <Spinner />
        </div>
      )}
      {alerts.data?.length === 0 && (
        <Card strong>
          <EmptyState
            message="Thiết bị này chưa có cảnh báo nào."
            description="Các cảnh báo mới sẽ xuất hiện tại đây sau khi máy gửi trạng thái lên hệ thống."
          />
        </Card>
      )}
      {alerts.data && alerts.data.length > 0 && (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="glass-strong flex min-w-0 items-center gap-3 rounded-glass p-4 ring-1 ring-inset ring-sky-200/70">
              <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-sky-100/80 text-sky-700">
                <Activity aria-hidden="true" className="size-5" />
              </span>
              <div>
                <p className="text-xs font-medium text-ink-muted">Tổng cảnh báo</p>
                <p className="text-xl font-bold text-ink">{alerts.data.length}</p>
              </div>
            </div>
            <div className="glass-strong flex min-w-0 items-center gap-3 rounded-glass p-4 ring-1 ring-inset ring-amber-200/70">
              <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-amber-100/80 text-amber-700">
                <ShieldAlert aria-hidden="true" className="size-5" />
              </span>
              <div>
                <p className="text-xs font-medium text-ink-muted">Đang diễn ra</p>
                <p className="text-xl font-bold text-ink">{activeCount}</p>
              </div>
            </div>
            <div className="glass-strong flex min-w-0 items-center gap-3 rounded-glass p-4 ring-1 ring-inset ring-emerald-200/70">
              <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-emerald-100/80 text-emerald-700">
                <CircleCheck aria-hidden="true" className="size-5" />
              </span>
              <div>
                <p className="text-xs font-medium text-ink-muted">Đã kết thúc</p>
                <p className="text-xl font-bold text-ink">{resolvedCount}</p>
              </div>
            </div>
          </div>
          <DeviceAlertList deviceName={alerts.data[0].device_name} alerts={alerts.data} />
        </>
      )}
    </div>
  )
}
