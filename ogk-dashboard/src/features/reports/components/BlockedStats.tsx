import type { Report } from '@/shared/types/reports.ts'

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="glass-input flex flex-col gap-1 rounded-control px-4 py-3">
      <span className="text-sm text-ink-muted">{label}</span>
      <span className="text-2xl font-bold text-ink">{value}</span>
    </div>
  )
}

export default function BlockedStats({ blocked }: { blocked: Report['blocked'] }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <Stat label="Tổng số lần bị chặn" value={blocked.total} />
      <Stat label="Ứng dụng bị chặn" value={blocked.apps} />
      <Stat label="Website bị chặn" value={blocked.domains} />
    </div>
  )
}
