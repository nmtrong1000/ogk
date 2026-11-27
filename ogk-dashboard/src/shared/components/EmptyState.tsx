import type { ReactNode } from 'react'
import { FileQuestion, type LucideIcon } from 'lucide-react'
import { cn } from '@/shared/utils/cn.ts'

type Props = {
  message: ReactNode
  description?: ReactNode
  action?: ReactNode
  icon?: LucideIcon
  compact?: boolean
  className?: string
}

export function EmptyState({
  message,
  description,
  action,
  icon: Icon = FileQuestion,
  compact = false,
  className,
}: Props) {
  return (
    <div
      role="status"
      className={cn(
        'flex w-full flex-col items-center justify-center gap-3 px-4 py-8 text-center',
        compact && 'gap-2 py-5',
        className,
      )}
    >
      <Icon aria-hidden="true" className={cn('size-14 text-brand-700', compact && 'size-12')} strokeWidth={1.8} />
      <div className="flex max-w-prose flex-col gap-1">
        <p className="text-base font-semibold text-ink">{message}</p>
        {description && <p className="text-sm leading-relaxed text-ink-muted">{description}</p>}
      </div>
      {action && <div className="pt-0.5">{action}</div>}
    </div>
  )
}
