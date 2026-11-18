import type { ReactNode } from 'react'
import { cn } from '@/shared/utils/cn.ts'

type Tone = 'error' | 'info' | 'success' | 'warning'

const TONES: Record<Tone, { box: string; icon: string }> = {
  error: { box: 'bg-rose-50/80 border-rose-200 text-rose-800', icon: '!' },
  warning: { box: 'bg-amber-50/80 border-amber-200 text-amber-900', icon: '!' },
  info: { box: 'bg-brand-50/80 border-brand-200 text-brand-800', icon: 'i' },
  success: { box: 'bg-emerald-50/80 border-emerald-200 text-emerald-800', icon: '✓' },
}

type Props = { tone?: Tone; title?: ReactNode; children?: ReactNode; className?: string }

export function Alert({ tone = 'info', title, children, className }: Props) {
  const { box, icon } = TONES[tone]
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      className={cn('flex gap-3 rounded-control border px-4 py-3 text-sm backdrop-blur-sm', box, className)}
    >
      <span
        aria-hidden
        className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full border border-current text-xs font-bold"
      >
        {icon}
      </span>
      <div className="min-w-0">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={title ? 'mt-0.5' : undefined}>{children}</div>}
      </div>
    </div>
  )
}
