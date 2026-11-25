import { useState, type FormEvent } from 'react'
import { Alert, Button, TextField } from '@/shared/components/index.ts'
import { MAX_QUOTA_MINUTES, QUOTA_ERROR, screentimeErrorMessage } from '@/features/screentime/utils/messages.ts'

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

function join(parts: Parts): number | null {
  if (!/^\d{1,2}$/.test(parts.hours) || !/^\d{1,2}$/.test(parts.minutes)) return null
  const minutes = Number(parts.minutes)
  const total = Number(parts.hours) * 60 + minutes
  return minutes < 60 && total <= MAX_QUOTA_MINUTES ? total : null
}

function QuotaRow({
  label,
  hint,
  parts,
  error,
  onChange,
}: {
  label: string
  hint: string
  parts: Parts
  error: string | null
  onChange: (parts: Parts) => void
}) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-sm font-semibold text-ink">{label}</legend>
      <p className="text-sm text-ink-muted">{hint}</p>
      <div className="grid grid-cols-2 gap-3 sm:max-w-sm">
        <TextField
          label="Giờ"
          inputMode="numeric"
          maxLength={2}
          value={parts.hours}
          error={error}
          onChange={(e) => onChange({ ...parts, hours: e.target.value.trim() })}
        />
        <TextField
          label="Phút"
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
  const [local, setLocal] = useState<{ weekday?: boolean; weekend?: boolean }>({})

  function submit(event: FormEvent) {
    event.preventDefault()
    const weekdayTotal = join(weekday)
    const weekendTotal = join(weekend)
    setLocal({ weekday: weekdayTotal === null, weekend: weekendTotal === null })
    if (weekdayTotal === null || weekendTotal === null) return
    onSubmit({ weekday_quota_minutes: weekdayTotal, weekend_quota_minutes: weekendTotal })
  }

  return (
    <form className="flex flex-col gap-5" onSubmit={submit} noValidate>
      {error != null && <Alert tone="error">{screentimeErrorMessage(error)}</Alert>}
      {saved && error == null && <Alert tone="success">Đã lưu giới hạn thời gian.</Alert>}
      <QuotaRow
        label="Ngày thường"
        hint="Thứ Hai đến thứ Sáu"
        parts={weekday}
        error={local.weekday ? QUOTA_ERROR : null}
        onChange={setWeekday}
      />
      <QuotaRow
        label="Cuối tuần"
        hint="Thứ Bảy và Chủ nhật"
        parts={weekend}
        error={local.weekend ? QUOTA_ERROR : null}
        onChange={setWeekend}
      />
      <div className="flex justify-end">
        <Button type="submit" loading={pending}>
          Lưu giới hạn
        </Button>
      </div>
    </form>
  )
}
