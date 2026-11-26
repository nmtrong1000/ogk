/*
 * Pairing flow: consent, create a code, then poll its status until the agent uses it.
 * Polling stops once the code is used or the countdown reaches zero.
 */
import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Alert, Button, Card, Checkbox } from '@/shared/components/index.ts'
import type { PairingCode } from '@/shared/types/enrollment.ts'
import { createPairingCode, getPairingCodeStatus, pairingCodeKey } from '@/features/enrollment/api.ts'
import AssignAccounts from '@/features/enrollment/components/AssignAccounts.tsx'
import { useCountdown } from '@/features/enrollment/hooks/useCountdown.ts'
import { formatRemaining } from '@/features/enrollment/utils/format.ts'
import { errorMessage } from '@/features/enrollment/utils/messages.ts'

const POLL_MS = 3000

type Issued = { code: PairingCode; deadline: number }

export default function AddDevicePage() {
  const [consent, setConsent] = useState(false)
  const [issued, setIssued] = useState<Issued | null>(null)
  const remaining = useCountdown(issued?.deadline ?? null)

  const create = useMutation({
    mutationFn: createPairingCode,
    onSuccess: (code) => setIssued({ code, deadline: Date.now() + code.expires_in * 1000 }),
  })
  const status = useQuery({
    queryKey: pairingCodeKey(issued?.code.id ?? 0),
    queryFn: () => getPairingCodeStatus(issued!.code.id),
    enabled: issued !== null,
    refetchInterval: (query) => (query.state.data?.status === 'pending' || !query.state.data ? POLL_MS : false),
  })

  const used = status.data?.status === 'used' && status.data.device_id !== null
  const expired = issued !== null && !used && (remaining === 0 || status.data?.status === 'expired')

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Thêm thiết bị</h1>
        <p className="mt-1 text-ink-muted">Ghép đôi máy tính Windows của con với tài khoản của bạn.</p>
      </div>

      {used ? (
        <Card title="Gán tài khoản Windows cho con">
          <AssignAccounts deviceId={status.data!.device_id!} />
        </Card>
      ) : (
        <Card title="Mã ghép đôi">
          <div className="flex flex-col gap-5">
            <ol className="list-decimal space-y-1 pl-5 text-sm text-ink-muted">
              <li>Trên máy của con, mở cửa sổ lệnh bằng quyền quản trị (Run as administrator).</li>
              <li>
                Chạy <code className="rounded bg-white/60 px-1.5 py-0.5 text-ink">ogk_service enroll</code> và nhập mã
                bên dưới.
              </li>
              <li>Mã chỉ dùng được một lần và hết hạn sau 10 phút.</li>
            </ol>

            {issued && !expired && (
              <div className="glass-strong flex flex-col items-center gap-2 rounded-glass py-6" aria-live="polite">
                <span className="font-mono text-4xl font-bold tracking-[0.2em] text-ink sm:text-5xl">
                  {issued.code.code}
                </span>
                <span className="text-sm text-ink-muted">
                  Còn <span className="font-semibold text-ink tabular-nums">{formatRemaining(remaining)}</span> · Đang
                  chờ máy của con nhập mã…
                </span>
              </div>
            )}
            {expired && <Alert tone="warning">Mã đã hết hạn. Tạo mã mới để tiếp tục.</Alert>}
            {create.isError && <Alert tone="error">{errorMessage(create.error)}</Alert>}
            {status.isError && <Alert tone="error">{errorMessage(status.error)}</Alert>}

            {(!issued || expired) && (
              <div className="flex flex-col gap-4">
                <Checkbox
                  label="Tôi là cha mẹ hoặc người giám hộ của con và đồng ý cài OGK để quản lý việc dùng máy tính của con trên thiết bị này."
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                />
                <div>
                  <Button disabled={!consent} loading={create.isPending} onClick={() => create.mutate()}>
                    {issued ? 'Tạo mã mới' : 'Tạo mã'}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}
