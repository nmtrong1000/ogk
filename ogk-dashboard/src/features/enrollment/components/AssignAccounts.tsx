import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { assignAccount, devicesKey, listDevices } from '@/shared/api/devices.ts'
import { AccountAssignments, Alert, Spinner } from '@/shared/components/index.ts'
import { childrenKey, listChildren } from '@/features/enrollment/api.ts'
import { errorMessage } from '@/features/enrollment/utils/messages.ts'

type Assignment = { accountId: number; childId: number | null }

export default function AssignAccounts({ deviceId }: { deviceId: number }) {
  const queryClient = useQueryClient()
  const devices = useQuery({ queryKey: devicesKey, queryFn: listDevices })
  const children = useQuery({ queryKey: childrenKey, queryFn: listChildren })
  const assign = useMutation({
    mutationFn: ({ accountId, childId }: Assignment) => assignAccount(deviceId, accountId, childId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: devicesKey }),
  })

  if (devices.isPending || children.isPending) {
    return (
      <div className="grid place-items-center py-6">
        <Spinner />
      </div>
    )
  }
  if (devices.isError) return <Alert tone="error">{errorMessage(devices.error)}</Alert>
  if (children.isError) return <Alert tone="error">{errorMessage(children.error)}</Alert>

  const device = devices.data.find((d) => d.id === deviceId)
  if (!device) return <Alert tone="error">Không tìm thấy thiết bị. Có thể đã bị gỡ.</Alert>

  return (
    <div className="flex flex-col gap-4">
      <p className="text-ink">
        Đã ghép đôi <strong>{device.name}</strong>. Chọn con dùng từng tài khoản Windows trên máy này.
      </p>
      {children.data.length === 0 && (
        <Alert tone="info">
          Chưa có con nào. <Link to="/children">Thêm con</Link> trước rồi quay lại gán.
        </Alert>
      )}
      {assign.isError && <Alert tone="error">{errorMessage(assign.error)}</Alert>}
      <AccountAssignments
        device={device}
        childOptions={children.data}
        pendingAccountId={assign.isPending ? (assign.variables?.accountId ?? null) : null}
        onAssign={(accountId, childId) => assign.mutate({ accountId, childId })}
      />
      <p className="text-sm">
        <Link to="/devices">Xem mọi thiết bị</Link>
      </p>
    </div>
  )
}
