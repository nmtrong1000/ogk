import { useId, type SelectHTMLAttributes } from 'react'
import { cn } from '@/shared/utils/cn.ts'
import { ToastMessage } from '@/shared/components/ToastProvider.tsx'

type Option = { value: string; label: string }

type Props = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string
  options: Option[]
  placeholder?: string
  hint?: string
  error?: string | null
}

export function Select({ label, options, placeholder, hint, error, id, className, required, ...rest }: Props) {
  const autoId = useId()
  const selectId = id ?? autoId
  const describedBy = !error && hint ? `${selectId}-hint` : undefined

  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <label htmlFor={selectId} className="text-sm font-medium text-ink">
        {label}
        {required && (
          <span aria-hidden="true" className="ml-0.5 text-rose-600">
            *
          </span>
        )}
      </label>
      <div className="relative">
        <select
          id={selectId}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={cn(
            'glass-input h-11 w-full cursor-pointer appearance-none rounded-control pr-10 pl-3.5 text-base text-ink',
            'transition outline-none focus:border-brand-400 focus:bg-white/90 focus:ring-4 focus:ring-brand-200/60',
            error && 'border-rose-400 focus:border-rose-400 focus:ring-rose-200/60',
          )}
          {...rest}
        >
          {placeholder !== undefined && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <svg
          aria-hidden
          viewBox="0 0 20 20"
          className="pointer-events-none absolute top-1/2 right-3.5 size-4 -translate-y-1/2 text-ink-muted"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="m5 8 5 5 5-5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      {error && <ToastMessage tone="error">{error}</ToastMessage>}
      {!error && hint && (
        <p id={`${selectId}-hint`} className="text-sm text-ink-muted">
          {hint}
        </p>
      )}
    </div>
  )
}
