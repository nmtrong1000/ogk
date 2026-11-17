import type { ReactNode } from 'react'
import { cn } from '../utils/cn.ts'

type Tone = 'neutral' | 'brand' | 'success' | 'warning' | 'danger'

const TONES: Record<Tone, string> = {
  neutral: 'bg-white/60 text-ink-muted ring-slate-300/60',
  brand: 'bg-brand-100/80 text-brand-700 ring-brand-300/60',
  success: 'bg-emerald-100/80 text-emerald-700 ring-emerald-300/60',
  warning: 'bg-amber-100/80 text-amber-800 ring-amber-300/60',
  danger: 'bg-rose-100/80 text-rose-700 ring-rose-300/60',
}

type Props = { tone?: Tone; children: ReactNode; className?: string }

export function Badge({ tone = 'neutral', children, className }: Props) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap ring-1 ring-inset',
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}
