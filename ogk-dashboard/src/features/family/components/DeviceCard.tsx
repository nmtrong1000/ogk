import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  BellRing,
  CalendarClock,
  ChevronDown,
  Clock3,
  Laptop,
  Unplug,
  UserRound,
  UsersRound,
  Wifi,
  WifiOff,
} from 'lucide-react'
import {
  Alert,
  Badge,
  Button,
  Dialog,
  EmptyState,
  Select,
  Table,
  TableBody,
  TableHead,
  TableRow,
  Td,
  Th,
} from '@/shared/components/index.ts'
import type { Child, Device } from '@/shared/types/family.ts'
import { formatDateTime } from '@/features/family/utils/time.ts'

type Props = {
  device: Device
  childOptions: Pick<Child, 'id' | 'name'>[]
  pendingAccountId: number | null
  removing: boolean
  removeError: string | null
  onAssign: (accountId: number, childId: number | null) => void
  onRemove: () => Promise<void>
}

const UNASSIGNED = ''

export default function DeviceCard({
  device,
  childOptions,
  pendingAccountId,
  removing,
  removeError,
  onAssign,
  onRemove,
}: Props) {
  const [accountsOpen, setAccountsOpen] = useState(false)
  const [confirmingRemove, setConfirmingRemove] = useState(false)
  const assignedCount = device.accounts.filter((account) => account.child_id !== null).length
  const options = [
    { value: UNASSIGNED, label: 'Chưa gán' },
    ...childOptions.map((child) => ({ value: String(child.id), label: child.name })),
  ]

  async function remove() {
    try {
      await onRemove()
      setConfirmingRemove(false)
    } catch {
      setConfirmingRemove(true)
    }
  }

  return (
    <article className="glass-strong min-w-0 rounded-glass p-5 shadow-glass ring-1 ring-inset ring-white/70 sm:p-7">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3.5">
          <span className="grid size-14 shrink-0 place-items-center rounded-2xl bg-linear-to-br from-sky-100/90 to-indigo-100/80 text-brand-700 shadow-control">
            <Laptop aria-hidden="true" className="size-8" strokeWidth={1.7} />
          </span>
          <div className="min-w-0 pt-0.5">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="break-words text-lg font-semibold tracking-tight text-ink sm:text-xl">{device.name}</h2>
              <Badge tone={device.last_seen_at ? 'success' : 'neutral'}>
                {device.last_seen_at ? <Wifi aria-hidden="true" className="size-3.5" /> : <WifiOff aria-hidden="true" className="size-3.5" />}
                {device.last_seen_at ? 'Đã từng kết nối' : 'Chưa kết nối'}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-ink-muted">Máy tính Windows đã ghép đôi với gia đình.</p>
          </div>
        </div>
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end">
          <Link
            to={`/devices/${device.id}/alerts`}
            className="inline-flex h-9 items-center gap-2 rounded-control glass-input px-3 text-sm font-semibold text-brand-700 transition hover:bg-white/90 hover:shadow-control"
          >
            <BellRing aria-hidden="true" className="size-4" />
            Cảnh báo
          </Link>
          <Button size="sm" variant="danger" disabled={removing} onClick={() => setConfirmingRemove(true)}>
            <Unplug aria-hidden="true" className="size-4" />
            Gỡ thiết bị
          </Button>
        </div>
      </header>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <div className="glass-input flex min-w-0 items-center gap-3 rounded-control p-3.5">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-white/75 text-brand-700">
            <CalendarClock aria-hidden="true" className="size-5" />
          </span>
          <div className="min-w-0">
            <p className="text-xs font-medium text-ink-muted">Ngày ghép đôi</p>
            <p className="mt-0.5 truncate text-sm font-semibold text-ink">{formatDateTime(device.created_at)}</p>
          </div>
        </div>
        <div className="glass-input flex min-w-0 items-center gap-3 rounded-control p-3.5">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-white/75 text-brand-700">
            <Clock3 aria-hidden="true" className="size-5" />
          </span>
          <div className="min-w-0">
            <p className="text-xs font-medium text-ink-muted">Hoạt động lần cuối</p>
            <p className="mt-0.5 truncate text-sm font-semibold text-ink">
              {device.last_seen_at ? formatDateTime(device.last_seen_at) : 'Chưa ghi nhận'}
            </p>
          </div>
        </div>
      </div>

      <section className="mt-5 overflow-hidden rounded-glass bg-white/45 ring-1 ring-inset ring-brand-100/80">
        <button
          type="button"
          aria-expanded={accountsOpen}
          aria-controls={`device-accounts-${device.id}`}
          className="flex w-full cursor-pointer items-center justify-between gap-3 px-4 py-3.5 text-left transition hover:bg-white/55 sm:px-5"
          onClick={() => setAccountsOpen((open) => !open)}
        >
          <span className="flex min-w-0 items-center gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-brand-100/80 text-brand-700">
              <UsersRound aria-hidden="true" className="size-5" />
            </span>
            <span className="min-w-0">
              <span className="flex flex-wrap items-center gap-2 font-semibold text-ink">
                Tài khoản Windows
                <Badge tone="brand">{device.accounts.length}</Badge>
              </span>
              <span className="mt-0.5 block text-xs text-ink-muted">
                {assignedCount} đã gán · {device.accounts.length - assignedCount} chưa gán
              </span>
            </span>
          </span>
          <ChevronDown
            aria-hidden="true"
            className={`size-5 shrink-0 text-ink-muted transition-transform duration-150 ${accountsOpen ? 'rotate-180' : ''}`}
          />
        </button>

        {accountsOpen && (
          <div id={`device-accounts-${device.id}`} className="border-t border-brand-100/80 px-4 py-3.5 sm:px-5">
            {device.accounts.length === 0 ? (
              <EmptyState message="Máy này chưa gửi tài khoản Windows nào." compact />
            ) : (
              <Table>
                <TableHead>
                  <tr>
                    <Th>Tài khoản Windows</Th>
                    <Th>Gán cho trẻ</Th>
                    <Th>Trạng thái</Th>
                  </tr>
                </TableHead>
                <TableBody>
                  {device.accounts.map((account) => (
                    <TableRow key={account.id}>
                      <Td className="min-w-44">
                        <span className="inline-flex items-center gap-2 font-medium">
                          <UserRound aria-hidden="true" className="size-4 shrink-0 text-brand-600" />
                          {account.username}
                        </span>
                      </Td>
                      <Td className="min-w-52">
                        <Select
                          label=""
                          aria-label={`Gán trẻ cho ${account.username}`}
                          options={options}
                          value={account.child_id === null ? UNASSIGNED : String(account.child_id)}
                          disabled={pendingAccountId === account.id}
                          onChange={(event) =>
                            onAssign(account.id, event.target.value === UNASSIGNED ? null : Number(event.target.value))
                          }
                        />
                      </Td>
                      <Td>
                        <Badge tone={account.child_id === null ? 'neutral' : 'success'}>
                          {account.child_id === null ? 'Chưa gán' : 'Đã gán'}
                        </Badge>
                      </Td>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        )}
      </section>

      <Dialog
        open={confirmingRemove}
        title={`Gỡ ${device.name}?`}
        onClose={() => !removing && setConfirmingRemove(false)}
        actions={
          <>
            <Button variant="ghost" disabled={removing} onClick={() => setConfirmingRemove(false)}>
              Hủy
            </Button>
            <Button variant="danger" loading={removing} onClick={remove}>
              <Unplug aria-hidden="true" className="size-4" />
              Gỡ thiết bị
            </Button>
          </>
        }
      >
        <p>Thiết bị sẽ bị gỡ khỏi danh sách và không thể tiếp tục gửi dữ liệu lên tài khoản gia đình này.</p>
        {removeError && (
          <Alert tone="error" className="mt-4">
            {removeError}
          </Alert>
        )}
      </Dialog>
    </article>
  )
}
