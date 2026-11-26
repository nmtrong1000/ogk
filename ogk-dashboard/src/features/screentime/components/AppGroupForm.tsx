import { useState, type FormEvent } from 'react'
import { Button, Card, TextField } from '@/shared/components/index.ts'
import { useToast } from '@/shared/components/ToastContext.ts'
import type { AppGroup, AppRule } from '@/shared/types/policy.ts'
import { appGroupBudgetInputSchema, appGroupNameSchema, appGroupsSchema } from '@/features/screentime/schemas.ts'

type Props = { groups: AppGroup[]; rules: AppRule[]; pending: boolean; onSave: (groups: AppGroup[]) => void }

export default function AppGroupForm({ groups, rules, pending, onSave }: Props) {
  const showToast = useToast()
  const [draft, setDraft] = useState(groups)
  const [name, setName] = useState('')

  function update(group: AppGroup, value: string) {
    const result = appGroupBudgetInputSchema.safeParse(value)
    if (!result.success) return
    setDraft(draft.map((item) => (item.id === group.id ? { ...item, budget_minutes: result.data } : item)))
  }

  function add(event: FormEvent) {
    event.preventDefault()
    const result = appGroupNameSchema(draft).safeParse(name)
    if (!result.success) {
      showToast({ tone: 'error', message: result.error.issues[0].message })
      return
    }
    setDraft([...draft, { id: `custom_${crypto.randomUUID()}`, name: result.data, budget_minutes: null }])
    setName('')
  }

  function save() {
    const result = appGroupsSchema.safeParse(draft)
    if (!result.success) {
      showToast({ tone: 'error', message: result.error.issues[0].message })
      return
    }
    onSave(result.data)
  }

  return (
    <div className="flex flex-col gap-4">
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
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <Button type="submit" loading={pending}>
          Tạo nhóm
        </Button>
      </form>
      <div className="flex justify-end">
        <Button type="button" loading={pending} disabled={pending} onClick={save}>
          Lưu nhóm và ngân sách
        </Button>
      </div>
    </div>
  )
}
