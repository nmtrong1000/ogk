import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Button } from '@/shared/components/index.ts'
import { formatDate } from '@/shared/utils/dateTime.ts'
import type { DayUsage, WeekUsage } from '@/shared/types/reports.ts'
import { formatDuration } from '@/shared/utils/duration.ts'

type Mode = 'day' | 'week'

type Point = { label: string; hours: number; seconds: number; weekStart?: string }

function points(mode: Mode, daily: DayUsage[], weekly: WeekUsage[]): Point[] {
  if (mode === 'day') {
    return daily.map((d) => ({ label: formatDate(d.date), hours: d.seconds / 3600, seconds: d.seconds }))
  }
  return weekly.map((w, index) => ({
    label: `Tuần ${index + 1}`,
    weekStart: formatDate(w.week_start),
    hours: w.seconds / 3600,
    seconds: w.seconds,
  }))
}

export default function UsageChart({ daily, weekly }: { daily: DayUsage[]; weekly: WeekUsage[] }) {
  const [mode, setMode] = useState<Mode>('day')
  const data = points(mode, daily, weekly)
  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-2" role="group" aria-label="Xem theo">
        <Button size="sm" variant={mode === 'day' ? 'primary' : 'secondary'} onClick={() => setMode('day')}>
          Theo ngày
        </Button>
        <Button size="sm" variant={mode === 'week' ? 'primary' : 'secondary'} onClick={() => setMode('week')}>
          Theo tuần
        </Button>
      </div>
      <div className="h-64 w-full sm:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 4, bottom: 0, left: -16 }}>
            <CartesianGrid vertical={false} stroke="var(--color-brand-100)" />
            <XAxis dataKey="label" tick={{ fontSize: 12 }} interval="preserveStartEnd" minTickGap={8} />
            <YAxis tick={{ fontSize: 12 }} allowDecimals={false} unit="h" />
            <Tooltip
              labelFormatter={(label, payload) => {
                const point = payload[0]?.payload as Point | undefined
                return point?.weekStart ? `${point.label} · bắt đầu ${point.weekStart}` : String(label)
              }}
              formatter={(_value, _name, item) => [formatDuration((item.payload as Point).seconds), 'Thời gian']}
              cursor={{ fill: 'var(--color-brand-50)' }}
            />
            <Bar dataKey="hours" fill="var(--color-brand-500)" radius={[6, 6, 0, 0]} maxBarSize={40} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
