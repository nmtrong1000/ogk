import { CircleAlert } from 'lucide-react'
import { cn } from '@/shared/utils/cn.ts'

type Props = {
  title: string
  message: string
  compact?: boolean
}

export default function ChildNotice({ title, message, compact = false }: Props) {
  return (
    <div
      role="alert"
      className={cn(
        'glass-strong w-full rounded-glass',
        compact
          ? 'flex items-start gap-4 p-4 text-left'
          : 'mx-auto flex max-w-lg flex-col items-center gap-4 px-6 py-8 text-center sm:px-10 sm:py-10',
      )}
    >
      <span
        className={cn(
          'grid shrink-0 place-items-center rounded-2xl bg-amber-100/80 text-amber-700 ring-1 ring-inset ring-amber-200/60',
          compact ? 'size-11 rounded-xl' : 'size-16',
        )}
      >
        <CircleAlert aria-hidden="true" className={compact ? 'size-5' : 'size-8'} strokeWidth={1.8} />
      </span>
      <div className={compact ? 'min-w-0 pt-0.5' : 'text-center'}>
        <h2 className={cn('font-bold tracking-tight text-ink', compact ? 'text-base' : 'text-xl sm:text-2xl')}>
          {title}
        </h2>
        <p className={cn('leading-6 text-ink-muted', compact ? 'mt-1 text-sm' : 'mx-auto mt-2 max-w-sm')}>{message}</p>
      </div>
    </div>
  )
}
