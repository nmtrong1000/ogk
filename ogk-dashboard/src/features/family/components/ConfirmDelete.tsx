import { useState } from 'react'
import { Button } from '@/shared/components/index.ts'

type Props = {
  name: string
  pending: boolean
  onConfirm: () => void
  size?: 'sm' | 'md'
  verb?: string
}

export default function ConfirmDelete({ name, pending, onConfirm, size = 'sm', verb = 'Xóa' }: Props) {
  const [asking, setAsking] = useState(false)
  if (!asking) {
    return (
      <Button size={size} variant="ghost" className="text-rose-600 hover:bg-rose-50/60" onClick={() => setAsking(true)}>
        {verb}
      </Button>
    )
  }
  return (
    <span
      className="inline-flex flex-wrap items-center justify-end gap-2"
      role="group"
      aria-label={`Xác nhận ${verb.toLowerCase()} ${name}`}
    >
      <span className="text-sm text-ink-muted">
        {verb} {name}?
      </span>
      <Button size={size} variant="danger" loading={pending} onClick={onConfirm}>
        {verb}
      </Button>
      <Button size={size} variant="ghost" disabled={pending} onClick={() => setAsking(false)}>
        Hủy
      </Button>
    </span>
  )
}
