/*
 * The one-time code arrives in the URL fragment. It is read once and removed with replaceState before the
 * exchange, so the history entry left behind never holds a code; the ref keeps StrictMode's second effect run
 * from exchanging, or finding no code and showing an error.
 */
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Card, Spinner } from '@/shared/components/index.ts'
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
    <Card strong className="mx-auto max-w-md text-center">
      {error ? (
        <Alert tone="warning">{childViewErrorMessage(error)}</Alert>
      ) : (
        <div className="flex flex-col items-center gap-3 py-6">
          <Spinner size="lg" />
          <p className="text-lg text-ink">Đang mở báo cáo của em...</p>
        </div>
      )}
    </Card>
  )
}
