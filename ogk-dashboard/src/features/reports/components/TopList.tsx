import { AppWindow } from 'lucide-react'
import { EmptyState } from '@/shared/components/index.ts'

type Item = { key: string; label: string; value: string; ratio: number }

export default function TopList({ items, empty }: { items: Item[]; empty: string }) {
  if (items.length === 0) return <EmptyState message={empty} icon={AppWindow} compact />
  return (
    <ol className="flex flex-col gap-3">
      {items.map((item, index) => (
        <li key={item.key} className="flex flex-col gap-1">
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className="min-w-0 truncate text-ink">
              <span className="mr-2 text-ink-muted">{index + 1}.</span>
              {item.label}
            </span>
            <span className="shrink-0 font-medium text-ink">{item.value}</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-brand-100">
            <div className="h-full rounded-full bg-brand-500" style={{ width: `${Math.max(4, item.ratio * 100)}%` }} />
          </div>
        </li>
      ))}
    </ol>
  )
}
