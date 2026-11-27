import { useState, type FormEvent } from 'react'
import { CalendarDays, CalendarRange } from 'lucide-react'
import { Alert, Button, TextField } from '@/shared/components/index.ts'
import { useToast } from '@/shared/components/ToastContext.ts'
import { screentimeErrorMessage } from '@/features/screentime/utils/messages.ts'
import { quotaFormSchema } from '@/features/screentime/schemas.ts'

export type Quotas = { weekday_quota_minutes: number; weekend_quota_minutes: number }

type Props = {
  initial: Quotas
  pending: boolean
  error: unknown
  saved: boolean
  onSubmit: (body: Quotas) => void
}

type Parts = { hours: string; minutes: string }

function split(total: number): Parts {
  return { hours: String(Math.floor(total / 60)), minutes: String(total % 60) }
}

function QuotaRow({
  label,
  hint,
  parts,
  onChange,
  icon: Icon,
  tint,
}: {
  label: string
  hint: string
  parts: Parts
  onChange: (parts: Parts) => void
  icon: typeof CalendarDays
  tint: 'sky' | 'violet'
}) {
  return (
    <fieldset
      className={`glass-strong min-w-0 rounded-glass p-4 ring-1 ring-inset ${tint === 'sky' ? 'ring-sky-200/70' : 'ring-violet-200/70'}`}
    >
      <legend className="sr-only">{label}</legend>
      <div className="mb-4 flex items-center gap-3">
        <span
          className={`grid size-10 shrink-0 place-items-center rounded-xl ${tint === 'sky' ? 'bg-sky-100/80 text-sky-700' : 'bg-violet-100/80 text-violet-700'}`}
        >
          <Icon aria-hidden="true" className="size-5" />
        </span>
        <div>
          <p className="font-semibold text-ink">{label}</p>
          <p className="text-sm text-ink-muted">{hint}</p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <TextField
          label="Giờ"
          required
          inputMode="numeric"
          maxLength={2}
          value={parts.hours}
          onChange={(e) => onChange({ ...parts, hours: e.target.value.trim() })}
        />
        <TextField
          label="Phút"
          required
          inputMode="numeric"
          maxLength={2}
          value={parts.minutes}
          onChange={(e) => onChange({ ...parts, minutes: e.target.value.trim() })}
        />
      </div>
    </fieldset>
  )
}

export default function QuotaForm({ initial, pending, error, saved, onSubmit }: Props) {
  const [weekday, setWeekday] = useState(split(initial.weekday_quota_minutes))
  const [weekend, setWeekend] = useState(split(initial.weekend_quota_minutes))
  const showToast = useToast()

  function submit(event: FormEvent) {
    event.preventDefault()
    const result = quotaFormSchema.safeParse({ weekday, weekend })
    if (!result.success) {
      showToast({ tone: 'error', message: result.error.issues[0].message })
      return
    }
    onSubmit({ weekday_quota_minutes: result.data.weekday, weekend_quota_minutes: result.data.weekend })
  }

  return (
    <form className="flex flex-col gap-5" onSubmit={submit} noValidate>
      {error != null && <Alert tone="error">{screentimeErrorMessage(error)}</Alert>}
      {saved && error == null && <Alert tone="success">Đã lưu giới hạn thời gian.</Alert>}
      <div className="grid gap-3 sm:grid-cols-2">
        <QuotaRow
          label="Ngày thường"
          hint="Thứ Hai đến thứ Sáu"
          parts={weekday}
          onChange={setWeekday}
          icon={CalendarDays}
          tint="sky"
        />
        <QuotaRow
          label="Cuối tuần"
          hint="Thứ Bảy và Chủ nhật"
          parts={weekend}
          onChange={setWeekend}
          icon={CalendarRange}
          tint="violet"
        />
      </div>
      <div className="flex justify-end">
        <Button type="submit" loading={pending}>
          Lưu giới hạn
        </Button>
      </div>
    </form>
  )
}
