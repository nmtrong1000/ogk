/*
 * Counts down from a duration the server gave (expires_in) instead of comparing expires_at with the
 * browser clock, so a parent's PC with a wrong clock still shows the right time left.
 */
import { useEffect, useState } from 'react'

export function useCountdown(deadline: number | null): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (deadline === null) return
    setNow(Date.now())
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [deadline])
  if (deadline === null) return 0
  return Math.max(0, Math.ceil((deadline - now) / 1000))
}
