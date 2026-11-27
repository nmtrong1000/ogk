import { createContext, useContext } from 'react'

export type ToastTone = 'error' | 'info' | 'success' | 'warning'
export type ToastInput = { tone: ToastTone; title?: string; message: string }
export type ToastContextValue = { showToast: (toast: ToastInput) => void }

export const ToastContext = createContext<ToastContextValue | null>(null)

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within ToastProvider')
  return context.showToast
}
