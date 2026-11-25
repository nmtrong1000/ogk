import { useState, type FormEvent } from 'react'
import { Alert, Button, Card, TextField } from '@/shared/components/index.ts'
import type { AppGroup, AppRule } from '@/shared/types/policy.ts'

type Props = { groups: AppGroup[]; rules: AppRule[]; pending: boolean; onSave: (groups: AppGroup[]) => void }

export default function AppGroupForm({ groups, rules, pending, onSave }: Props) {
  const [draft, setDraft] = useState(groups)
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)

  function update(group: AppGroup, value: string) {
    const minutes = value === '' ? null : Number(value)
    if (minutes !== null && (!Number.isInteger(minutes) || minutes < 0 || minutes > 1440)) return
    setDraft(draft.map((item) => (item.id === group.id ? { ...item, budget_minutes: minutes } : item)))
  }

  function add(event: FormEvent) {
    event.preventDefault()
    const normalized = name.trim()
    if (
      !normalized ||
      normalized.length > 40 ||
      draft.some((group) => group.name.toLocaleLowerCase() === normalized.toLocaleLowerCase())
    ) {
      setError('Tên nhóm phải dài từ 1 đến 40 ký tự và chưa được sử dụng.')
      return
    }
    setDraft([...draft, { id: `custom_${crypto.randomUUID()}`, name: normalized, budget_minutes: null }])
    setName('')
    setError(null)
  }

  return (
    <div className="flex flex-col gap-4">
      {error && <Alert tone="error">{error}</Alert>}
      <div className="grid gap-3 sm:grid-cols-2">
        {draft.map((group) => {
          const assigned = rules.some((rule) => rule.group_id === group.id)
          return (
            <Card
              key={group.id}
              title={group.name}
              description={group.id.startsWith('custom_') ? 'Nhóm tùy chỉnh' : 'Nhóm mặc định'}
            >
              <div className="flex items-end gap-3">
                <TextField
                  label="Ngân sách mỗi ngày (phút)"
                  type="number"
                  min={0}
                  max={1440}
                  value={group.budget_minutes ?? ''}
                  placeholder="Không giới hạn"
                  hint="Để trống nếu không giới hạn."
                  disabled={pending}
                  onChange={(event) => update(group, event.target.value)}
                />
                {group.id.startsWith('custom_') && (
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={pending || assigned}
                    title={assigned ? 'Hãy chuyển ứng dụng khác trước khi xóa nhóm.' : undefined}
                    onClick={() => setDraft(draft.filter((item) => item.id !== group.id))}
                  >
                    Xóa
                  </Button>
                )}
              </div>
              {assigned && <p className="mt-2 text-sm text-ink-muted">Có ứng dụng được gán vào nhóm này.</p>}
            </Card>
          )
        })}
      </div>
      <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={add}>
        <TextField
          label="Tên nhóm tùy chỉnh"
          maxLength={40}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <Button type="submit" loading={pending}>
          Tạo nhóm
        </Button>
      </form>
      <div className="flex justify-end">
        <Button type="button" loading={pending} disabled={pending} onClick={() => onSave(draft)}>
          Lưu nhóm và ngân sách
        </Button>
      </div>
    </div>
  )
}
