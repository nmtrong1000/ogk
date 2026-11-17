import type { InputHTMLAttributes } from 'react'
import { cn } from '../utils/cn.ts'

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & { label: string }

export function Checkbox({ label, className, ...rest }: Props) {
  return (
    <label className={cn('inline-flex cursor-pointer items-center gap-2.5 text-sm text-ink select-none', className)}>
      <input type="checkbox" className="size-4.5 cursor-pointer rounded accent-brand-500" {...rest} />
      {label}
    </label>
  )
}
