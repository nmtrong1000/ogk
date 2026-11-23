import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { childDevicesKey, listChildDevices } from '@/shared/api/devices.ts'
import { Alert, Card, Spinner } from '@/shared/components/index.ts'
import { deviceErrorMessage } from '@/features/family/utils/messages.ts'
import CommandControls from '@/features/commands/components/CommandControls.tsx'

export default function ChildDevices({ childId }: { childId: number }) {
  const devices = useQuery({ queryKey: childDevicesKey(childId), queryFn: () => listChildDevices(childId) })
  return (
    <Card title="Thiết bị" actions={<Link to="/devices">Quản lý thiết bị</Link>}>
      {devices.isPending && (
        <div className="grid place-items-center py-6">
          <Spinner />
        </div>
      )}
      {devices.isError && <Alert tone="error">{deviceErrorMessage(devices.error)}</Alert>}
      {devices.data?.length === 0 && (
        <p className="text-sm text-ink-muted">Chưa có tài khoản Windows nào được gán cho con.</p>
      )}
      {devices.data && devices.data.length > 0 && (
        <ul className="flex flex-col gap-2">
          {devices.data.map((device) => (
            <li key={device.id} className="flex flex-wrap items-baseline gap-x-2">
              <span className="font-medium text-ink">{device.name}</span>
              <span className="text-sm text-ink-muted">
                Tài khoản:{' '}
                {device.accounts
                  .filter((a) => a.child_id === childId)
                  .map((a) => a.username)
                  .join(', ')}
              </span>
              <CommandControls deviceId={device.id} childId={childId} />
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
