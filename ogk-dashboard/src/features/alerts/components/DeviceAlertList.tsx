import { Clock3, ShieldAlert } from 'lucide-react'
import { Badge, Card } from '@/shared/components/index.ts'
import { formatDateTime } from '@/shared/utils/dateTime.ts'
import type { DeviceAlert } from '@/shared/types/alerts.ts'
import { alertDetail, alertTypeLabel } from '@/features/alerts/utils/messages.ts'

type Props = { deviceName: string; alerts: DeviceAlert[] }

function AlertRow({ alert }: { alert: DeviceAlert }) {
  const detail = alertDetail(alert)
  const open = alert.resolved_at === null
  const Icon = alert.type === 'clock_tampered' ? Clock3 : ShieldAlert
  return (
    <li className="flex min-w-0 gap-3.5 py-4 first:pt-0 last:pb-0 sm:gap-4">
      <span
        className={`grid size-11 shrink-0 place-items-center rounded-2xl ${open ? 'bg-rose-100/80 text-rose-700' : 'bg-slate-100/80 text-slate-600'}`}
      >
        <Icon aria-hidden="true" className="size-5" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-semibold text-ink">{alertTypeLabel(alert.type)}</h3>
          <Badge tone={open ? 'warning' : 'success'}>{open ? 'Đang diễn ra' : 'Đã kết thúc'}</Badge>
        </div>
        <div className="mt-1 flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-muted sm:flex-nowrap">
          {detail && (
            <span className="w-full whitespace-normal break-words text-sm sm:min-w-0 sm:flex-1">{detail}</span>
          )}
          <span className="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap">
            <Clock3 aria-hidden="true" className="size-3.5" />
            Bắt đầu {formatDateTime(alert.first_seen_at)}
          </span>
          <span aria-hidden="true" className="shrink-0 text-ink-subtle">
            ·
          </span>
          <span className="shrink-0 whitespace-nowrap">
            {open
              ? `Ghi nhận gần nhất ${formatDateTime(alert.last_seen_at)}`
              : `Kết thúc ${formatDateTime(alert.resolved_at as string)}`}
          </span>
        </div>
      </div>
    </li>
  )
}

export default function DeviceAlertList({ deviceName, alerts }: Props) {
  const openCount = alerts.filter((a) => a.resolved_at === null).length
  return (
    <Card
      strong
      title={deviceName}
      description={openCount > 0 ? `${openCount} cảnh báo đang diễn ra` : 'Không có cảnh báo đang diễn ra'}
      actions={<Badge tone={openCount > 0 ? 'danger' : 'success'}>{alerts.length} cảnh báo</Badge>}
    >
      <ul className="flex flex-col divide-y divide-white/80">
        {alerts.map((alert) => (
          <AlertRow key={alert.id} alert={alert} />
        ))}
      </ul>
    </Card>
  )
}
