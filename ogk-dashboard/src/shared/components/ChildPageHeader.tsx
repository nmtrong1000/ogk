import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'

type Props = {
  title: string
  description: ReactNode
  icon: LucideIcon
  actions?: ReactNode
}

export function ChildPageHeader({ title, description, icon: Icon, actions }: Props) {
  return (
    <section className="glass-strong flex flex-col gap-4 rounded-glass p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
      <div className="flex min-w-0 items-center gap-4">
        <span className="grid size-14 shrink-0 place-items-center rounded-2xl bg-linear-to-br from-brand-100 to-sky-100 text-brand-700 shadow-control sm:size-16">
          <Icon aria-hidden="true" className="size-8" strokeWidth={1.8} />
        </span>
        <div className="min-w-0">
          <p className="text-xs font-bold tracking-[0.16em] text-brand-700 uppercase">Quản lý trẻ</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-ink sm:text-3xl">{title}</h1>
          <p className="mt-1 max-w-2xl text-sm text-ink-muted">{description}</p>
        </div>
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2 sm:justify-end">{actions}</div>}
    </section>
  )
}
