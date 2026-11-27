/*
 * Pairing flow: consent, create a code, then poll its status until the agent uses it.
 * Polling stops once the code is used or the countdown reaches zero.
 */
import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Check, Clock3, Laptop, QrCode, ShieldCheck, Terminal } from 'lucide-react'
import { Alert, Badge, Button, Card, Checkbox } from '@/shared/components/index.ts'
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
  const steps = [
    {
      number: '01',
      icon: ShieldCheck,
      title: 'Xác nhận quyền giám hộ',
      description: 'Đồng ý cài OGK và quản lý việc sử dụng máy tính của con.',
    },
    {
      number: '02',
      icon: Terminal,
      title: 'Nhập mã trên máy Windows',
      description: 'Mở cửa sổ lệnh bằng quyền quản trị rồi chạy ogk_service enroll.',
    },
    {
      number: '03',
      icon: Laptop,
      title: 'Gán tài khoản cho con',
      description: 'Sau khi ghép đôi, chọn trẻ dùng từng tài khoản Windows trên máy.',
    },
  ]

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Thêm thiết bị</h1>
        <p className="mt-1 text-ink-muted">Kết nối máy tính Windows với gia đình trong vài bước.</p>
      </div>

      {used ? (
        <Card
          strong
          title="Thiết bị đã ghép đôi"
          description="Chọn trẻ dùng từng tài khoản Windows trên máy này."
        >
          <AssignAccounts deviceId={status.data!.device_id!} />
        </Card>
      ) : (
        <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(18rem,0.85fr)]">
          <Card strong title="Quy trình ghép đôi" description="Làm theo các bước dưới đây để kết nối máy của con.">
            <ol className="flex flex-col gap-3">
              {steps.map(({ number, icon: Icon, title, description }, index) => (
                <li key={number} className="glass-input flex min-w-0 items-start gap-3.5 rounded-control p-4">
                  <span
                    className={`grid size-11 shrink-0 place-items-center rounded-xl ${index === 0 && (!issued || expired) ? 'bg-brand-100/80 text-brand-700' : 'bg-white/75 text-ink-muted'}`}
                  >
                    <Icon aria-hidden="true" className="size-5" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-bold tracking-wide text-brand-700">BƯỚC {number}</span>
                      {index === 0 && consent && <Check aria-label="Đã xác nhận" className="size-4 text-emerald-600" />}
                      {index === 1 && issued && !expired && (
                        <Badge tone="warning">
                          <Clock3 aria-hidden="true" className="size-3.5" />
                          Đang chờ
                        </Badge>
                      )}
                      {index === 2 && used && <Badge tone="success">Hoàn tất</Badge>}
                    </span>
                    <span className="mt-1 block font-semibold text-ink">{title}</span>
                    <span className="mt-0.5 block text-sm leading-5 text-ink-muted">
                      {index === 1 ? (
                        <>
                          {description.split('ogk_service enroll')[0]}
                          <code className="rounded bg-white/70 px-1.5 py-0.5 font-medium text-ink">ogk_service enroll</code>
                          .
                        </>
                      ) : (
                        description
                      )}
                    </span>
                  </span>
                </li>
              ))}
            </ol>
          </Card>

          <Card
            strong
            title={issued && !expired ? 'Mã ghép đôi' : 'Tạo mã ghép đôi'}
            description={issued && !expired ? 'Nhập mã này trên máy tính Windows của con.' : 'Mã có hiệu lực trong 10 phút và chỉ dùng được một lần.'}
          >
            <div className="flex flex-col gap-5">
              {issued && !expired ? (
                <>
                  <div className="glass-strong flex min-h-40 flex-col items-center justify-center gap-3 rounded-glass px-3 py-6" aria-live="polite">
                    <span className="grid size-12 place-items-center rounded-2xl bg-brand-100/80 text-brand-700">
                      <Laptop aria-hidden="true" className="size-6" />
                    </span>
                    <span className="break-all text-center font-mono text-3xl font-bold tracking-[0.16em] text-ink sm:text-4xl">
                      {issued.code.code}
                    </span>
                    <Badge tone="warning">
                      <Clock3 aria-hidden="true" className="size-3.5" />
                      Còn {formatRemaining(remaining)}
                    </Badge>
                  </div>
                  <p className="text-center text-sm text-ink-muted">Đang chờ máy của con nhập mã ghép đôi…</p>
                </>
              ) : (
                <>
                  {expired && <Alert tone="warning">Mã đã hết hạn. Tạo mã mới để tiếp tục.</Alert>}
                  {create.isError && <Alert tone="error">{errorMessage(create.error)}</Alert>}
                  {status.isError && <Alert tone="error">{errorMessage(status.error)}</Alert>}
                  <div className="rounded-control bg-brand-50/70 p-4 ring-1 ring-inset ring-brand-100/80">
                    <Checkbox
                      className="items-start leading-5"
                      label="Tôi là cha mẹ hoặc người giám hộ của con và đồng ý cài OGK để quản lý việc dùng máy tính của con trên thiết bị này."
                      checked={consent}
                      onChange={(e) => setConsent(e.target.checked)}
                    />
                  </div>
                  <Button block disabled={!consent} loading={create.isPending} onClick={() => create.mutate()}>
                    <QrCode aria-hidden="true" className="size-4" />
                    {issued ? 'Tạo mã mới' : 'Tạo mã ghép đôi'}
                  </Button>
                </>
              )}
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
