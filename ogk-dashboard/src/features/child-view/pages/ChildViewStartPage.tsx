/*
 * The one-time code arrives in the URL fragment. It is read once and removed with replaceState before the
 * exchange, so the history entry left behind never holds a code; the ref keeps StrictMode's second effect run
 * from exchanging, or finding no code and showing an error.
 */
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CircleAlert } from 'lucide-react'
import { Spinner } from '@/shared/components/index.ts'
import { getChildViewMe, openChildView } from '@/features/child-view/api.ts'
import { childViewErrorMessage } from '@/features/child-view/utils/messages.ts'

function takeCode(): string | null {
  const code = new URLSearchParams(window.location.hash.slice(1)).get('code')
  window.history.replaceState(window.history.state, '', window.location.pathname)
  return code
}

export default function ChildViewStartPage() {
  const navigate = useNavigate()
  const started = useRef(false)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    if (started.current) return
    started.current = true
    const code = takeCode()
    const open = code ? openChildView(code) : getChildViewMe()
    open.then(() => navigate('/child-view', { replace: true })).catch(setError)
  }, [navigate])

  return (
    <div className="grid min-h-[min(62dvh,38rem)] place-items-center py-8">
      {error ? (
        <section
          role="alert"
          className="glass-strong w-full max-w-lg rounded-glass px-6 py-8 text-center shadow-glass sm:px-10 sm:py-10"
        >
          <span className="mx-auto grid size-16 place-items-center rounded-2xl bg-amber-100/80 text-amber-700 ring-1 ring-inset ring-amber-200/60">
            <CircleAlert aria-hidden="true" className="size-8" strokeWidth={1.8} />
          </span>
          <h1 className="mt-5 text-xl font-bold tracking-tight text-ink sm:text-2xl">Không thể mở báo cáo</h1>
          <p className="mx-auto mt-2 max-w-sm leading-6 text-ink-muted">{childViewErrorMessage(error)}</p>
        </section>
      ) : (
        <div className="glass-strong flex w-full max-w-lg flex-col items-center gap-4 rounded-glass px-6 py-10 text-center shadow-glass sm:px-10">
          <Spinner size="lg" />
          <p className="text-lg font-medium text-ink">Đang mở báo cáo của em...</p>
        </div>
      )}
    </div>
  )
}
