import { Badge, Button, Card } from '@/shared/components/index.ts'
import { AppWindow, ArrowRight, CalendarDays, CalendarRange, Clock3 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { Policy } from '@/shared/types/policy.ts'
import { DAY_LABELS, describeDay, formatDateTime, formatMinutes, openHours } from '@/shared/utils/schedule.ts'
import { setterLabel } from '@/features/policy/utils/messages.ts'

export default function PolicySummary({ policy }: { policy: Policy }) {
  const navigate = useNavigate()
  return (
    <Card
      title="Chính sách hiện tại"
      description={`Cập nhật ${formatDateTime(policy.updated_at)} bởi ${setterLabel(policy.set_by)}`}
      actions={<Badge tone="brand">Phiên bản {policy.policy_version}</Badge>}
    >
      <p className="mb-4 text-sm text-ink-muted">
        Lịch quy định giờ được dùng; hạn mức quy định tổng thời gian trong ngày. Máy cần thỏa mãn cả hai điều kiện, nên
        lịch cả ngày vẫn không bỏ hạn mức.
      </p>
      <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="glass-strong rounded-glass p-4 ring-1 ring-inset ring-sky-200/70">
          <div className="flex items-center gap-3">
            <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-sky-100/80 text-sky-700">
              <CalendarDays aria-hidden="true" className="size-5" />
            </span>
            <dt className="text-sm font-medium text-ink-muted">Ngày thường (T2–T6)</dt>
          </div>
          <dd className="mt-4 text-3xl font-bold tracking-tight text-sky-800">
            {formatMinutes(policy.weekday_quota_minutes)}
          </dd>
          <p className="mt-1 text-sm text-ink-muted">mỗi ngày</p>
        </div>
        <div className="glass-strong rounded-glass p-4 ring-1 ring-inset ring-violet-200/70">
          <div className="flex items-center gap-3">
            <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-violet-100/80 text-violet-700">
              <CalendarRange aria-hidden="true" className="size-5" />
            </span>
            <dt className="text-sm font-medium text-ink-muted">Cuối tuần (T7, CN)</dt>
          </div>
          <dd className="mt-4 text-3xl font-bold tracking-tight text-violet-800">
            {formatMinutes(policy.weekend_quota_minutes)}
          </dd>
          <p className="mt-1 text-sm text-ink-muted">mỗi ngày</p>
        </div>
        <div className="glass-strong rounded-glass p-4 ring-1 ring-inset ring-emerald-200/70">
          <div className="flex items-center gap-3">
            <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-emerald-100/80 text-emerald-700">
              <Clock3 aria-hidden="true" className="size-5" />
            </span>
            <dt className="text-sm font-medium text-ink-muted">Tổng giờ mở theo lịch</dt>
          </div>
          <dd className="mt-4 text-3xl font-bold tracking-tight text-emerald-800">
            {openHours(policy.weekly_schedule)} giờ
          </dd>
          <p className="mt-1 text-sm text-ink-muted">mỗi tuần</p>
        </div>
        <div className="glass-strong rounded-glass p-4 ring-1 ring-inset ring-rose-200/70">
          <div className="flex items-center gap-3">
            <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-rose-100/80 text-rose-700">
              <AppWindow aria-hidden="true" className="size-5" />
            </span>
            <dt className="text-sm font-medium text-ink-muted">Ứng dụng</dt>
          </div>
          <dd className="mt-4 flex flex-wrap gap-2 text-sm font-semibold">
            <span className="rounded-full bg-rose-100/80 px-2.5 py-1 text-rose-700">
              {policy.app_rules.filter((rule) => rule.action === 'block').length} bị chặn
            </span>
            <span className="rounded-full bg-emerald-100/80 px-2.5 py-1 text-emerald-700">
              {policy.app_rules.filter((rule) => rule.action === 'allow').length} cho phép
            </span>
          </dd>
          <p className="mt-1 text-sm text-ink-muted">luật ứng dụng</p>
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
      <div className="mt-5 flex justify-end">
        <Button onClick={() => navigate(`/children/${policy.child_id}/screentime`)}>
          Sửa thời gian dùng máy
          <ArrowRight aria-hidden="true" className="size-4" />
        </Button>
      </div>
    </Card>
  )
}
