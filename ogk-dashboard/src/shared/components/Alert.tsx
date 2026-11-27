import type { ReactNode } from 'react'
import type { ToastTone } from '@/shared/components/ToastContext.ts'
import { ToastMessage } from '@/shared/components/ToastProvider.tsx'

type Props = { tone?: ToastTone; title?: ReactNode; children?: ReactNode; className?: string }

export function Alert({ tone = 'info', title, children, className }: Props) {
  void className
  return (
    <ToastMessage tone={tone} title={typeof title === 'string' ? title : undefined}>
      {children}
    </ToastMessage>
  )
}
