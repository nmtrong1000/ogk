import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/shared/utils/cn.ts'

type Props = Omit<HTMLAttributes<HTMLElement>, 'title'> & {
  title?: ReactNode
  description?: ReactNode
  actions?: ReactNode
  strong?: boolean
}

export function Card({ title, description, actions, strong = false, className, children, ...rest }: Props) {
  return (
    <section className={cn(strong ? 'glass-strong' : 'glass', 'rounded-glass p-5 sm:p-7', className)} {...rest}>
      {(title || actions) && (
        <header className="mb-5 flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            {title && <h2 className="text-lg font-semibold tracking-tight text-ink">{title}</h2>}
            {description && <p className="mt-1 text-sm text-ink-muted">{description}</p>}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  )
}
