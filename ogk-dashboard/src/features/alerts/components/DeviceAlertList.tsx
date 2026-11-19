import { Badge, Card } from '@/shared/components/index.ts'
import type { DeviceAlert } from '@/shared/types/alerts.ts'
import { alertDetail, alertTypeLabel, formatDateTime } from '@/features/alerts/utils/messages.ts'

type Props = { deviceName: string; alerts: DeviceAlert[] }

function AlertRow({ alert }: { alert: DeviceAlert }) {
  const detail = alertDetail(alert)
  const open = alert.resolved_at === null
  return (
    <li className="flex flex-col gap-1 py-3 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={open ? 'danger' : 'neutral'}>{alertTypeLabel(alert.type)}</Badge>
        <Badge tone={open ? 'warning' : 'success'}>{open ? 'Đang diễn ra' : 'Đã hết'}</Badge>
      </div>
      {detail && <p className="text-sm text-ink">{detail}</p>}
      <p className="text-xs text-ink-muted">
        Bắt đầu {formatDateTime(alert.first_seen_at)} ·{' '}
        {open
          ? `Ghi nhận gần nhất ${formatDateTime(alert.last_seen_at)}`
          : `Kết thúc ${formatDateTime(alert.resolved_at as string)}`}
      </p>
    </li>
  )
}

export default function DeviceAlertList({ deviceName, alerts }: Props) {
  const openCount = alerts.filter((a) => a.resolved_at === null).length
  return (
    <Card
      title={deviceName}
      description={openCount > 0 ? `${openCount} cảnh báo đang diễn ra` : 'Không có cảnh báo đang diễn ra'}
    >
      <ul className="flex flex-col divide-y divide-slate-200/70">
        {alerts.map((alert) => (
          <AlertRow key={alert.id} alert={alert} />
        ))}
      </ul>
    </Card>
  )
}
