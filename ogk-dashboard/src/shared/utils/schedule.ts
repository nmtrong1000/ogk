/*
 * weekly_schedule is 7 strings of 48 '0'/'1' slots, index 0 = Monday, slot k = [k*30 min, (k+1)*30 min) on the
 * child's PC clock. This must match docs/protocol.md.
 */
export const DAYS = 7
export const SLOTS = 48
export const DAY_LABELS = ['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ nhật']
export const DAY_SHORT = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']
export const WEEKDAYS = [0, 1, 2, 3, 4]
export const OPEN_DAY = '1'.repeat(SLOTS)
export const CLOSED_DAY = '0'.repeat(SLOTS)

export function slotTime(slot: number): string {
  const minutes = slot * 30
  return `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`
}

export function dayRanges(day: string): string[] {
  const ranges: string[] = []
  let start: number | null = null
  for (let slot = 0; slot <= SLOTS; slot++) {
    const open = slot < SLOTS && day[slot] === '1'
    if (open && start === null) start = slot
    if (!open && start !== null) {
      ranges.push(`${slotTime(start)}–${slot === SLOTS ? '24:00' : slotTime(slot)}`)
      start = null
    }
  }
  return ranges
}

export function describeDay(day: string): string {
  const ranges = dayRanges(day)
  if (ranges.length === 0) return 'Khóa cả ngày'
  if (day === OPEN_DAY) return 'Cả ngày'
  return ranges.join(', ')
}

export function openHours(schedule: string[]): number {
  return schedule.reduce((total, day) => total + [...day].filter((c) => c === '1').length, 0) / 2
}

export function formatMinutes(minutes: number): string {
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  if (hours === 0) return `${rest} phút`
  return rest === 0 ? `${hours} giờ` : `${hours} giờ ${rest} phút`
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('vi-VN')
}
