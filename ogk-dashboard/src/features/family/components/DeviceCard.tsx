import { AccountAssignments, Card } from '@/shared/components/index.ts'
import type { Child, Device } from '@/shared/types/family.ts'
import ConfirmDelete from '@/features/family/components/ConfirmDelete.tsx'
import { formatDateTime } from '@/features/family/utils/time.ts'

type Props = {
  device: Device
  childOptions: Pick<Child, 'id' | 'name'>[]
  pendingAccountId: number | null
  removing: boolean
  onAssign: (accountId: number, childId: number | null) => void
  onRemove: () => void
}

export default function DeviceCard({ device, childOptions, pendingAccountId, removing, onAssign, onRemove }: Props) {
  return (
    <Card
      title={device.name}
      description={
        <>
          Ghép đôi lúc {formatDateTime(device.created_at)} ·{' '}
          {device.last_seen_at ? `Hoạt động lần cuối ${formatDateTime(device.last_seen_at)}` : 'Chưa kết nối'}
        </>
      }
      actions={<ConfirmDelete name={device.name} verb="Gỡ" pending={removing} onConfirm={onRemove} />}
    >
      <AccountAssignments
        device={device}
        childOptions={childOptions}
        pendingAccountId={pendingAccountId}
        onAssign={onAssign}
      />
    </Card>
  )
}
