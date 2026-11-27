/*
 * Desktop paints by dragging: the first cell decides open or closed for the whole stroke. Touch keeps pointer
 * capture on the first element, so the cell under the finger is found with elementFromPoint and data-* attributes.
 * Phones get one day at a time with large tap targets and no dragging, so the page can still scroll.
 */
import { useRef, useState, type PointerEvent } from 'react'
import { Alert, Button, Select } from '@/shared/components/index.ts'
import { useToast } from '@/shared/components/ToastContext.ts'
import {
  CLOSED_DAY,
  DAY_LABELS,
  DAY_SHORT,
  DAYS,
  OPEN_DAY,
  SLOTS,
  WEEKDAYS,
  describeDay,
  slotTime,
} from '@/shared/utils/schedule.ts'
import { cn } from '@/shared/utils/cn.ts'
import { screentimeErrorMessage } from '@/features/screentime/utils/messages.ts'
import { weeklyScheduleSchema } from '@/features/screentime/schemas.ts'

type Props = {
  initial: string[]
  pending: boolean
  error: unknown
  saved: boolean
  onSubmit: (schedule: string[]) => void
}

function setSlot(days: string[], day: number, slot: number, open: boolean): string[] {
  const value = open ? '1' : '0'
  if (days[day][slot] === value) return days
  const next = [...days]
  next[day] = days[day].slice(0, slot) + value + days[day].slice(slot + 1)
  return next
}

function cellLabel(day: number, slot: number, open: boolean): string {
  const end = slot + 1 === SLOTS ? '24:00' : slotTime(slot + 1)
  return `${DAY_LABELS[day]} ${slotTime(slot)}–${end}: ${open ? 'được dùng' : 'khóa'}`
}

function cellFrom(target: Element | null): { day: number; slot: number } | null {
  const cell = target?.closest<HTMLElement>('[data-day][data-slot]')
  if (!cell) return null
  return { day: Number(cell.dataset.day), slot: Number(cell.dataset.slot) }
}

function DesktopGrid({ days, onChange }: { days: string[]; onChange: (days: string[]) => void }) {
  const paint = useRef<boolean | null>(null)

  function apply(target: Element | null) {
    const cell = cellFrom(target)
    if (cell === null || paint.current === null) return
    onChange(setSlot(days, cell.day, cell.slot, paint.current))
  }

  function down(event: PointerEvent<HTMLDivElement>) {
    const cell = cellFrom(event.target as Element)
    if (cell === null) return
    event.preventDefault()
    paint.current = days[cell.day][cell.slot] !== '1'
    apply(event.target as Element)
  }

  function move(event: PointerEvent<HTMLDivElement>) {
    if (paint.current === null) return
    apply(document.elementFromPoint(event.clientX, event.clientY))
  }

  function up() {
    paint.current = null
  }

  return (
    <div
      className="hidden touch-none select-none sm:grid"
      style={{ gridTemplateColumns: `3rem repeat(${SLOTS}, minmax(0, 1fr))` }}
      onPointerDown={down}
      onPointerMove={move}
      onPointerUp={up}
      onPointerCancel={up}
      onPointerLeave={up}
    >
      <div />
      {Array.from({ length: SLOTS }, (_, slot) => (
        <div key={slot} className="h-5 text-[10px] text-ink-muted">
          {slot % 4 === 0 ? slot / 2 : ''}
        </div>
      ))}
      {days.map((day, d) => (
        <div key={DAY_LABELS[d]} className="contents">
          <div className="flex items-center text-xs font-semibold text-ink">{DAY_SHORT[d]}</div>
          {[...day].map((value, slot) => (
            <button
              key={slot}
              type="button"
              data-day={d}
              data-slot={slot}
              aria-pressed={value === '1'}
              aria-label={cellLabel(d, slot, value === '1')}
              title={cellLabel(d, slot, value === '1')}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  onChange(setSlot(days, d, slot, value !== '1'))
                }
              }}
              className={cn(
                'h-7 cursor-pointer border-y border-r border-white/70 first-of-type:border-l',
                slot % 2 === 0 && 'border-r-white/30',
                value === '1' ? 'bg-brand-400 hover:bg-brand-500' : 'bg-white/50 hover:bg-brand-100',
                'focus-visible:relative focus-visible:z-10 focus-visible:outline-2 focus-visible:outline-brand-600',
              )}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

function PhoneDay({ day, index, onChange }: { day: string; index: number; onChange: (slot: number) => void }) {
  return (
    <div className="grid grid-cols-4 gap-1.5 sm:hidden">
      {[...day].map((value, slot) => (
        <button
          key={slot}
          type="button"
          aria-pressed={value === '1'}
          aria-label={cellLabel(index, slot, value === '1')}
          onClick={() => onChange(slot)}
          className={cn(
            'h-11 rounded-lg text-sm font-medium tabular-nums transition',
            value === '1' ? 'bg-brand-400 text-white' : 'glass-input text-ink-muted',
          )}
        >
          {slotTime(slot)}
        </button>
      ))}
    </div>
  )
}

export default function ScheduleGrid({ initial, pending, error, saved, onSubmit }: Props) {
  const showToast = useToast()
  const [days, setDays] = useState(initial)
  const [selected, setSelected] = useState(0)
  const dirty = days.some((day, i) => day !== initial[i])

  function setDay(index: number, value: string) {
    setDays(days.map((day, i) => (i === index ? value : day)))
  }

  function copyTo(targets: number[]) {
    setDays(days.map((day, i) => (targets.includes(i) ? days[selected] : day)))
  }

  function submit() {
    const result = weeklyScheduleSchema.safeParse(days)
    if (!result.success) {
      showToast({ tone: 'error', message: result.error.issues[0].message })
      return
    }
    onSubmit(result.data)
  }

  return (
    <div className="flex flex-col gap-5">
      {error != null && <Alert tone="error">{screentimeErrorMessage(error)}</Alert>}
      {saved && error == null && !dirty && <Alert tone="success">Đã lưu lịch tuần.</Alert>}
      <div className="flex items-center gap-4 text-sm text-ink-muted">
        <span className="inline-flex items-center gap-1.5">
          <span className="size-3 rounded-sm bg-brand-400" /> Được dùng
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="glass-input size-3 rounded-sm" /> Khóa
        </span>
      </div>
      <p className="hidden text-sm text-ink-muted sm:block">
        Bấm hoặc kéo qua các ô để đổi. Mỗi ô là 30 phút; số trên đầu cột là giờ.
      </p>
      <DesktopGrid days={days} onChange={setDays} />

      <div className="flex flex-col gap-3 border-t border-brand-100/80 pt-4">
        <div className="grid gap-3 sm:grid-cols-[14rem_1fr] sm:items-end">
          <Select
            label="Ngày"
            options={DAY_LABELS.map((label, i) => ({ value: String(i), label }))}
            value={String(selected)}
            onChange={(e) => setSelected(Number(e.target.value))}
          />
          <p className="text-sm text-ink-muted sm:pb-3">{describeDay(days[selected])}</p>
        </div>
        <PhoneDay
          day={days[selected]}
          index={selected}
          onChange={(slot) => setDays(setSlot(days, selected, slot, days[selected][slot] !== '1'))}
        />
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" size="sm" onClick={() => setDay(selected, OPEN_DAY)}>
            Mở cả ngày
          </Button>
          <Button variant="secondary" size="sm" onClick={() => setDay(selected, CLOSED_DAY)}>
            Khóa cả ngày
          </Button>
          <Button variant="secondary" size="sm" onClick={() => copyTo(WEEKDAYS)}>
            Chép sang T2–T6
          </Button>
          <Button variant="secondary" size="sm" onClick={() => copyTo(Array.from({ length: DAYS }, (_, i) => i))}>
            Chép sang cả tuần
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap justify-end gap-2">
        <Button variant="ghost" disabled={!dirty || pending} onClick={() => setDays(initial)}>
          Hoàn tác
        </Button>
        <Button loading={pending} disabled={!dirty} onClick={submit}>
          Lưu lịch
        </Button>
      </div>
    </div>
  )
}
