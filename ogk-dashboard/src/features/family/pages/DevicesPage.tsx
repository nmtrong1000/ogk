/*
 * All active devices with per-account child assignment and removal.
 * Removing a device revokes its tokens on the server, so the agent on that PC stops working.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Laptop, Plus, UsersRound, Wifi } from 'lucide-react'
import { assignAccount, devicesKey, listDevices, removeDevice } from '@/shared/api/devices.ts'
import { Alert, Card, EmptyState, Spinner } from '@/shared/components/index.ts'
import { childrenKey, listChildren } from '@/features/family/api.ts'
import DeviceCard from '@/features/family/components/DeviceCard.tsx'
import { deviceErrorMessage } from '@/features/family/utils/messages.ts'

type Assignment = { deviceId: number; accountId: number; childId: number | null }

export default function DevicesPage() {
  const queryClient = useQueryClient()
  const devices = useQuery({ queryKey: devicesKey, queryFn: listDevices })
  const children = useQuery({ queryKey: childrenKey, queryFn: listChildren })

  const assign = useMutation({
    mutationFn: ({ deviceId, accountId, childId }: Assignment) => assignAccount(deviceId, accountId, childId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: devicesKey }),
  })
  const remove = useMutation({
    mutationFn: removeDevice,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: devicesKey }),
  })

  const error = devices.error ?? children.error
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Danh sách thiết bị</h1>
          <p className="mt-1 text-ink-muted">Theo dõi máy tính đã ghép đôi và phân công tài khoản Windows.</p>
        </div>
        <Link
          to="/devices/add"
          className="inline-flex h-10 items-center gap-2 rounded-control bg-linear-to-r from-brand-500 to-brand-400 px-4 text-sm font-semibold text-white no-underline shadow-control transition hover:shadow-control-hover hover:brightness-105"
        >
          <Plus aria-hidden="true" className="size-4" />
          Thêm thiết bị
        </Link>
      </div>

      {assign.isError && <Alert tone="error">{deviceErrorMessage(assign.error)}</Alert>}
      {error && <Alert tone="error">{deviceErrorMessage(error)}</Alert>}
      {(devices.isPending || children.isPending) && !error && (
        <div className="grid place-items-center py-12">
          <Spinner />
        </div>
      )}
      {devices.data?.length === 0 && (
        <Card>
          <EmptyState
            message="Chưa có thiết bị nào."
            description="Ghép đôi máy đầu tiên để bắt đầu quản lý."
            action={
              <Link
                to="/devices/add"
                className="font-semibold text-brand-700 underline underline-offset-4 hover:text-brand-800"
              >
                Thêm thiết bị
              </Link>
            }
          />
        </Card>
      )}
      {devices.data && devices.data.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="glass-strong flex items-center gap-3 rounded-glass p-4 ring-1 ring-inset ring-sky-200/70">
            <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-sky-100/80 text-sky-700">
              <Laptop aria-hidden="true" className="size-5" />
            </span>
            <div>
              <p className="text-xs font-medium text-ink-muted">Máy đã ghép đôi</p>
              <p className="text-xl font-bold text-ink">{devices.data.length}</p>
            </div>
          </div>
          <div className="glass-strong flex items-center gap-3 rounded-glass p-4 ring-1 ring-inset ring-emerald-200/70">
            <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-emerald-100/80 text-emerald-700">
              <Wifi aria-hidden="true" className="size-5" />
            </span>
            <div>
              <p className="text-xs font-medium text-ink-muted">Đã có kết nối</p>
              <p className="text-xl font-bold text-ink">
                {devices.data.filter((device) => device.last_seen_at !== null).length}
              </p>
            </div>
          </div>
          <div className="glass-strong flex items-center gap-3 rounded-glass p-4 ring-1 ring-inset ring-violet-200/70">
            <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-violet-100/80 text-violet-700">
              <UsersRound aria-hidden="true" className="size-5" />
            </span>
            <div>
              <p className="text-xs font-medium text-ink-muted">Tài khoản đã gán</p>
              <p className="text-xl font-bold text-ink">
                {devices.data.reduce(
                  (count, device) => count + device.accounts.filter((account) => account.child_id !== null).length,
                  0,
                )}
              </p>
            </div>
          </div>
        </div>
      )}
      {devices.data &&
        children.data &&
        devices.data.map((device) => (
          <DeviceCard
            key={device.id}
            device={device}
            childOptions={children.data}
            pendingAccountId={
              assign.isPending && assign.variables?.deviceId === device.id ? assign.variables.accountId : null
            }
            removing={remove.isPending && remove.variables === device.id}
            removeError={remove.isError && remove.variables === device.id ? deviceErrorMessage(remove.error) : null}
            onAssign={(accountId, childId) => assign.mutate({ deviceId: device.id, accountId, childId })}
            onRemove={() => {
              remove.reset()
              return remove.mutateAsync(device.id)
            }}
          />
        ))}
    </div>
  )
}
