import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Laptop, Settings2, UserRound } from 'lucide-react'
import { childDevicesKey, listChildDevices } from '@/shared/api/devices.ts'
import { Alert, EmptyState, Spinner } from '@/shared/components/index.ts'
import { deviceErrorMessage } from '@/features/family/utils/messages.ts'
import CommandControls from '@/features/commands/components/CommandControls.tsx'

export default function ChildDevices({ childId }: { childId: number }) {
  const devices = useQuery({ queryKey: childDevicesKey(childId), queryFn: () => listChildDevices(childId) })
  return (
    <section className="glass rounded-glass p-5 sm:p-7">
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-ink">Thiết bị</h2>
          <p className="mt-1 text-sm text-ink-muted">Máy tính Windows được liên kết với trẻ.</p>
        </div>
        <Link className="inline-flex items-center gap-1.5 text-sm font-semibold" to="/devices">
          <Settings2 aria-hidden="true" className="size-4" />
          Quản lý thiết bị
        </Link>
      </header>
      {devices.isPending && (
        <div className="grid place-items-center py-6">
          <Spinner />
        </div>
      )}
      {devices.isError && <Alert tone="error">{deviceErrorMessage(devices.error)}</Alert>}
      {devices.data?.length === 0 && (
        <EmptyState message="Chưa có tài khoản Windows nào được gán cho con." icon={Laptop} compact />
      )}
      {devices.data && devices.data.length > 0 && (
        <ul className="grid gap-4">
          {devices.data.map((device) => (
            <li key={device.id} className="glass-strong grid gap-4 rounded-glass p-4 sm:grid-cols-[auto_1fr] sm:gap-5 sm:p-5">
              <div className="grid size-20 place-items-center self-start rounded-3xl bg-linear-to-br from-sky-100/90 to-indigo-100/80 text-brand-700 shadow-control sm:size-24">
                <Laptop aria-hidden="true" className="size-14 sm:size-16" strokeWidth={1.6} />
              </div>
              <div className="flex min-w-0 flex-col">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h3 className="truncate text-lg font-semibold text-ink">{device.name}</h3>
                    <p className="mt-1 text-sm text-ink-muted">Máy tính Windows</p>
                  </div>
                  <span className="rounded-full bg-white/60 px-3 py-1 text-xs font-medium text-ink-muted">
                    {device.last_seen_at
                      ? `Hoạt động ${new Date(device.last_seen_at).toLocaleString('vi-VN')}`
                      : 'Chưa ghi nhận hoạt động'}
                  </span>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {device.accounts
                    .filter((account) => account.child_id === childId)
                    .map((account) => (
                    <span
                      key={account.id}
                      className="inline-flex items-center gap-1.5 rounded-full bg-white/65 px-3 py-1.5 text-sm text-ink-muted"
                    >
                      <UserRound aria-hidden="true" className="size-4 text-brand-600" />
                      {account.username}
                    </span>
                    ))}
                </div>
                <div className="mt-5 flex justify-end">
                  <CommandControls deviceId={device.id} childId={childId} />
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
