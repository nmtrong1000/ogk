export const DATE_FORMATS = {
  dateTime: 'YYYY-MM-DD HH:mm:ss',
  date: 'YYYY-MM-DD',
  time: 'HH:mm',
} as const

type DateParts = {
  YYYY: string
  MM: string
  DD: string
  HH: string
  mm: string
  ss: string
}

function pad(value: number): string {
  return String(value).padStart(2, '0')
}

function render(format: string, parts: DateParts): string {
  return format.replace(/YYYY|MM|DD|HH|mm|ss/g, (token) => parts[token as keyof DateParts])
}

function parseDate(value: string | number | Date): Date | null {
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value
  if (typeof value === 'string') {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
    if (match) {
      const [, year, month, day] = match
      const date = new Date(Number(year), Number(month) - 1, Number(day))
      if (date.getFullYear() !== Number(year) || date.getMonth() !== Number(month) - 1 || date.getDate() !== Number(day)) {
        return null
      }
      return date
    }
  }
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function partsOf(date: Date): DateParts {
  return {
    YYYY: String(date.getFullYear()).padStart(4, '0'),
    MM: pad(date.getMonth() + 1),
    DD: pad(date.getDate()),
    HH: pad(date.getHours()),
    mm: pad(date.getMinutes()),
    ss: pad(date.getSeconds()),
  }
}

export function formatDateTime(value: string | number | Date | null | undefined): string {
  if (value === null || value === undefined) return ''
  const date = parseDate(value)
  return date ? render(DATE_FORMATS.dateTime, partsOf(date)) : ''
}

export function formatDate(value: string | number | Date | null | undefined): string {
  if (value === null || value === undefined) return ''
  const date = parseDate(value)
  return date ? render(DATE_FORMATS.date, partsOf(date)) : ''
}

export function formatTime(value: string | number | Date | null | undefined): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') {
    const match = /^(\d{2}):(\d{2})(?::\d{2})?$/.exec(value)
    if (match) {
      const hours = Number(match[1])
      const minutes = Number(match[2])
      if (hours > 23 || minutes > 59) return ''
      return render(DATE_FORMATS.time, { YYYY: '', MM: '', DD: '', HH: pad(hours), mm: pad(minutes), ss: '00' })
    }
  }
  const date = parseDate(value)
  return date ? render(DATE_FORMATS.time, partsOf(date)) : ''
}

export function formatClock(minutesAfterMidnight: number): string {
  if (!Number.isFinite(minutesAfterMidnight) || minutesAfterMidnight < 0 || minutesAfterMidnight >= 1440) return ''
  const hours = Math.floor(minutesAfterMidnight / 60)
  const minutes = minutesAfterMidnight % 60
  return render(DATE_FORMATS.time, { YYYY: '', MM: '', DD: '', HH: pad(hours), mm: pad(minutes), ss: '00' })
}
