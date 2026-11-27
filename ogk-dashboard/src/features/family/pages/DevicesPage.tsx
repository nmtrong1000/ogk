/*
 * All active devices with per-account child assignment and removal.
 * Removing a device revokes its tokens on the server, so the agent on that PC stops working.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
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
          <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Thiết bị</h1>
          <p className="mt-1 text-ink-muted">Máy tính đã ghép đôi và con dùng từng tài khoản Windows.</p>
        </div>
        <Link
          to="/devices/add"
          className="rounded-control bg-brand-500 px-4 py-2 text-sm font-semibold text-white no-underline shadow-control hover:bg-brand-600 hover:text-white"
        >
          Thêm thiết bị
        </Link>
      </div>

      {assign.isError && <Alert tone="error">{deviceErrorMessage(assign.error)}</Alert>}
      {remove.isError && <Alert tone="error">{deviceErrorMessage(remove.error)}</Alert>}
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
              <Link to="/devices/add" className="font-semibold text-brand-700 underline underline-offset-4 hover:text-brand-800">
                Thêm thiết bị
              </Link>
            }
          />
        </Card>
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
            onAssign={(accountId, childId) => assign.mutate({ deviceId: device.id, accountId, childId })}
            onRemove={() => remove.mutate(device.id)}
          />
        ))}
    </div>
  )
}
