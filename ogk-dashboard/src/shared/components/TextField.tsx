import { useId, type InputHTMLAttributes } from 'react'
import { cn } from '@/shared/utils/cn.ts'
import { ToastMessage } from '@/shared/components/ToastProvider.tsx'

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label: string
  hint?: string
  error?: string | null
}

export function TextField({ label, hint, error, id, className, required, ...rest }: Props) {
  const autoId = useId()
  const inputId = id ?? autoId
  const describedBy = !error && hint ? `${inputId}-hint` : undefined

  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <label htmlFor={inputId} className="text-sm font-medium text-ink">
        {label}
        {required && (
          <span aria-hidden="true" className="ml-0.5 text-rose-600">
            *
          </span>
        )}
      </label>
      <input
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={cn(
          'glass-input h-11 rounded-control px-3.5 text-base text-ink placeholder:text-ink-subtle',
          'transition outline-none focus:border-brand-400 focus:bg-white/90 focus:ring-4 focus:ring-brand-200/60',
          error && 'border-rose-400 focus:border-rose-400 focus:ring-rose-200/60',
        )}
        {...rest}
      />
      {error && <ToastMessage tone="error">{error}</ToastMessage>}
      {!error && hint && (
        <p id={`${inputId}-hint`} className="text-xs text-ink-subtle">
          {hint}
        </p>
      )}
    </div>
  )
}
