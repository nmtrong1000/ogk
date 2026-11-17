import type { ButtonHTMLAttributes } from 'react'
import { cn } from '../utils/cn.ts'
import { Spinner } from './Spinner.tsx'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'sm' | 'md' | 'lg'

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant
  size?: Size
  loading?: boolean
  block?: boolean
}

const VARIANTS: Record<Variant, string> = {
  primary:
    'text-white bg-linear-to-r from-brand-500 to-brand-400 shadow-control hover:shadow-control-hover hover:brightness-105',
  secondary: 'glass-input text-brand-700 hover:bg-white/90 hover:border-brand-300',
  ghost: 'text-brand-700 hover:bg-white/50',
  danger: 'text-white bg-linear-to-r from-rose-500 to-rose-400 shadow-sm hover:brightness-105',
}

const SIZES: Record<Size, string> = {
  sm: 'h-8 px-3 text-sm gap-1.5',
  md: 'h-10 px-4 text-sm gap-2',
  lg: 'h-12 px-6 text-base gap-2',
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  block = false,
  disabled,
  className,
  children,
  type = 'button',
  ...rest
}: Props) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        'inline-flex cursor-pointer items-center justify-center rounded-control font-semibold whitespace-nowrap',
        'transition duration-150 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60 disabled:active:scale-100',
        VARIANTS[variant],
        SIZES[size],
        block && 'w-full',
        className,
      )}
      {...rest}
    >
      {loading && <Spinner size="sm" label="Đang xử lý" />}
      {children}
    </button>
  )
}
