import { cn } from '../utils/cn.ts'

type Props = { size?: 'sm' | 'md' | 'lg'; label?: string; className?: string }

const SIZES = { sm: 'size-4 border-2', md: 'size-6 border-2', lg: 'size-10 border-[3px]' }

export function Spinner({ size = 'md', label = 'Đang tải', className }: Props) {
  return (
    <span role="status" className={cn('inline-flex items-center', className)}>
      <span
        aria-hidden
        className={cn(
          'animate-spin rounded-full border-brand-200 border-t-brand-500 motion-reduce:animate-none',
          SIZES[size],
        )}
      />
      <span className="sr-only">{label}</span>
    </span>
  )
}
