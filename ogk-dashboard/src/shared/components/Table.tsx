import type { HTMLAttributes, TdHTMLAttributes, ThHTMLAttributes } from 'react'
import { cn } from '../utils/cn.ts'

export function Table({ className, children, ...rest }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="-mx-5 overflow-x-auto px-5 sm:-mx-7 sm:px-7">
      <table className={cn('w-full border-collapse text-left text-sm', className)} {...rest}>
        {children}
      </table>
    </div>
  )
}

export function TableHead(props: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead {...props} />
}

export function TableBody(props: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody {...props} />
}

export function TableRow({ className, ...rest }: HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn('border-b border-brand-100/80 transition-colors last:border-0 hover:bg-white/40', className)}
      {...rest}
    />
  )
}

export function Th({ className, ...rest }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn(
        'border-b border-brand-200/70 px-3 py-2.5 text-xs font-semibold tracking-wide text-ink-muted uppercase',
        className,
      )}
      {...rest}
    />
  )
}

export function Td({ className, ...rest }: TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn('px-3 py-3 align-middle break-words text-ink', className)} {...rest} />
}
