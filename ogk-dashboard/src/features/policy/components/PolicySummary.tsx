import { Badge, Card } from '@/shared/components/index.ts'
import type { Policy } from '@/shared/types/policy.ts'
import { DAY_LABELS, describeDay, formatDateTime, formatMinutes, openHours } from '@/shared/utils/schedule.ts'
import { setterLabel } from '@/features/policy/utils/messages.ts'

export default function PolicySummary({ policy }: { policy: Policy }) {
  return (
    <Card
      title="Chính sách hiện tại"
      description={`Cập nhật ${formatDateTime(policy.updated_at)} bởi ${setterLabel(policy.set_by)}`}
      actions={<Badge tone="brand">Phiên bản {policy.policy_version}</Badge>}
    >
      <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <dt className="text-sm text-ink-muted">Ngày thường (T2–T6)</dt>
          <dd className="mt-1 text-lg font-semibold text-ink">
            {formatMinutes(policy.weekday_quota_minutes)} mỗi ngày
          </dd>
        </div>
        <div>
          <dt className="text-sm text-ink-muted">Cuối tuần (T7, CN)</dt>
          <dd className="mt-1 text-lg font-semibold text-ink">
            {formatMinutes(policy.weekend_quota_minutes)} mỗi ngày
          </dd>
        </div>
        <div>
          <dt className="text-sm text-ink-muted">Khung giờ cho phép</dt>
          <dd className="mt-1 text-lg font-semibold text-ink">{openHours(policy.weekly_schedule)} giờ mỗi tuần</dd>
        </div>
        <div>
          <dt className="text-sm text-ink-muted">Ứng dụng</dt>
          <dd className="mt-1 text-lg font-semibold text-ink">
            {policy.app_rules.filter((r) => r.action === 'block').length} bị chặn,{' '}
            {policy.app_rules.filter((r) => r.action === 'allow').length} cho phép
          </dd>
        </div>
      </dl>
      <ul className="mt-6 divide-y divide-brand-100/80">
        {policy.weekly_schedule.map((day, index) => (
          <li key={DAY_LABELS[index]} className="flex flex-wrap justify-between gap-2 py-2.5 text-sm">
            <span className="font-medium text-ink">{DAY_LABELS[index]}</span>
            <span className="text-ink-muted">{describeDay(day)}</span>
          </li>
        ))}
      </ul>
    </Card>
  )
}
