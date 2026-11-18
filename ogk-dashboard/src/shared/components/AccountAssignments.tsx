import { Select } from '@/shared/components/Select.tsx'
import type { Child, Device } from '@/shared/types/family.ts'

type Props = {
  device: Device
  childOptions: Pick<Child, 'id' | 'name'>[]
  pendingAccountId: number | null
  onAssign: (accountId: number, childId: number | null) => void
}

const UNASSIGNED = ''

export function AccountAssignments({ device, childOptions, pendingAccountId, onAssign }: Props) {
  if (device.accounts.length === 0) {
    return <p className="text-sm text-ink-muted">Máy này không gửi tài khoản Windows nào.</p>
  }
  const options = [
    { value: UNASSIGNED, label: 'Chưa gán' },
    ...childOptions.map((c) => ({ value: String(c.id), label: c.name })),
  ]
  return (
    <ul className="grid gap-3 sm:grid-cols-2">
      {device.accounts.map((account) => (
        <li key={account.id}>
          <Select
            label={`Tài khoản Windows: ${account.username}`}
            options={options}
            value={account.child_id === null ? UNASSIGNED : String(account.child_id)}
            disabled={pendingAccountId === account.id}
            onChange={(e) => onAssign(account.id, e.target.value === UNASSIGNED ? null : Number(e.target.value))}
          />
        </li>
      ))}
    </ul>
  )
}
