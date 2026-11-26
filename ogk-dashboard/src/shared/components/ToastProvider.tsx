import { CircleAlert, CircleCheck, Info, TriangleAlert, X } from 'lucide-react'
import { isValidElement, useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { ToastContext, type ToastInput, type ToastTone, useToast } from '@/shared/components/ToastContext.ts'
import { cn } from '@/shared/utils/cn.ts'

type ToastItem = ToastInput & { id: number }

const TONES: Record<ToastTone, { icon: typeof CircleAlert; label: string; iconStyle: string }> = {
  error: { icon: CircleAlert, label: 'Đã xảy ra lỗi', iconStyle: 'bg-rose-50 text-rose-600' },
  info: { icon: Info, label: 'Thông tin', iconStyle: 'bg-sky-50 text-sky-600' },
  success: {
    icon: CircleCheck,
    label: 'Thành công',
    iconStyle: 'bg-emerald-50 text-emerald-600',
  },
  warning: {
    icon: TriangleAlert,
    label: 'Lưu ý',
    iconStyle: 'bg-amber-50 text-amber-600',
  },
}

function ToastCard({ toast, onDismiss }: { toast: ToastItem; onDismiss: (id: number) => void }) {
  const { icon: Icon, label, iconStyle } = TONES[toast.tone]
  const [isLeaving, setIsLeaving] = useState(false)

  const dismiss = useCallback(() => {
    if (isLeaving) return
    setIsLeaving(true)
    window.setTimeout(() => onDismiss(toast.id), 180)
  }, [isLeaving, onDismiss, toast.id])

  useEffect(() => {
    if (isLeaving) return
    const timer = window.setTimeout(dismiss, 5000)
    return () => window.clearTimeout(timer)
  }, [dismiss, isLeaving])

  return (
    <div
      role={toast.tone === 'error' ? 'alert' : 'status'}
      className={cn(
        'relative flex w-full items-start gap-4 overflow-hidden rounded-2xl bg-white px-5 py-4',
        'shadow-[0_18px_48px_rgba(15,41,66,0.18),0_3px_10px_rgba(15,41,66,0.09)]',
        isLeaving ? 'toast-exit' : 'toast-enter',
      )}
    >
      <span className={cn('grid size-11 shrink-0 place-items-center rounded-xl', iconStyle)}>
        <Icon aria-hidden="true" className="size-5" strokeWidth={2.2} />
      </span>
      <div className="min-w-0 flex-1 pt-0.5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">{toast.title ?? label}</p>
        <p className="mt-1 text-sm leading-5 text-slate-700 [text-wrap:pretty]">{toast.message}</p>
      </div>
      <button
        type="button"
        aria-label="Đóng thông báo"
        className="-mr-2 -mt-2 grid size-10 shrink-0 place-items-center rounded-xl text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 active:scale-95"
        onClick={dismiss}
      >
        <X aria-hidden="true" className="size-4" />
      </button>
    </div>
  )
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const showToast = useCallback((input: ToastInput) => {
    setToasts((current) => {
      return [...current.slice(-2), { ...input, id: Date.now() + Math.random() }]
    })
  }, [])
  const dismissToast = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div
        aria-label="Thông báo"
        className="pointer-events-none fixed inset-x-4 bottom-14 z-50 flex flex-col items-end gap-3 sm:inset-x-auto sm:right-6 sm:w-[min(26rem,calc(100vw-3rem))]"
      >
        {toasts.map((toast) => (
          <div key={toast.id} className="pointer-events-auto w-full">
            <ToastCard toast={toast} onDismiss={dismissToast} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

function textContent(node: ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(textContent).join('')
  if (isValidElement<{ children?: ReactNode }>(node)) return textContent(node.props.children)
  return ''
}

export function ToastMessage({
  tone = 'info',
  title,
  children,
}: {
  tone?: ToastTone
  title?: string
  children?: ReactNode
}) {
  const showToast = useToast()
  const lastNotification = useRef<string | null>(null)
  const message = textContent(children) || ''
  const signature = `${tone}:${title ?? ''}:${message}`

  useEffect(() => {
    if (lastNotification.current === signature) return
    lastNotification.current = signature
    showToast({ tone, title, message })
  }, [message, showToast, signature, title, tone])

  return null
}
