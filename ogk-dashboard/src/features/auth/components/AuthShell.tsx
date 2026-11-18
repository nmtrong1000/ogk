import type { ReactNode } from 'react'
import { Card } from '@/shared/components/index.ts'

type Props = { title: string; subtitle: string; footer: ReactNode; children: ReactNode }

export default function AuthShell({ title, subtitle, footer, children }: Props) {
  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-5 pt-2 sm:pt-8">
      <div className="text-center">
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">{title}</h1>
        <p className="mt-1.5 text-ink-muted">{subtitle}</p>
      </div>
      <Card strong>{children}</Card>
      <p className="text-center text-sm text-ink-muted">{footer}</p>
    </div>
  )
}
