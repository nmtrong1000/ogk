import { useEffect, useId, useRef, type ReactNode } from 'react'
import { cn } from '../utils/cn.ts'

type Props = {
  open: boolean
  title: ReactNode
  children?: ReactNode
  actions?: ReactNode
  onClose: () => void
  className?: string
}

export function Dialog({ open, title, children, actions, onClose, className }: Props) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onCancel={(e) => {
        e.preventDefault()
        onClose()
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
      className={cn(
        'glass-strong m-auto w-[calc(100%-2rem)] max-w-md rounded-glass p-0 text-ink',
        'backdrop:bg-ink/30 backdrop:backdrop-blur-sm',
        className,
      )}
    >
      <div className="p-6">
        <h2 id={titleId} className="text-lg font-semibold tracking-tight">
          {title}
        </h2>
        {children && <div className="mt-2 text-sm text-ink-muted">{children}</div>}
        {actions && <div className="mt-6 flex flex-wrap justify-end gap-2">{actions}</div>}
      </div>
    </dialog>
  )
}
