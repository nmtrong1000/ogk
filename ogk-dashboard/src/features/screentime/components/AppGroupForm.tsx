import { useState, type FormEvent } from 'react'
import {
  BookOpen,
  CircleHelp,
  Clapperboard,
  CirclePlus,
  FolderCog,
  Gamepad2,
  MessagesSquare,
  Plus,
  Save,
  ShieldAlert,
  Shapes,
  Trash2,
  type LucideIcon,
} from 'lucide-react'
import { Badge, Button, Card, Dialog, TextField } from '@/shared/components/index.ts'
import { useToast } from '@/shared/components/ToastContext.ts'
import type { AppGroup, AppRule } from '@/shared/types/policy.ts'
import { appGroupBudgetInputSchema, appGroupNameSchema, appGroupsSchema } from '@/features/screentime/schemas.ts'

type Props = { groups: AppGroup[]; rules: AppRule[]; pending: boolean; onSave: (groups: AppGroup[]) => void }

const groupIcons: Record<string, LucideIcon> = {
  education: BookOpen,
  entertainment: Clapperboard,
  social: MessagesSquare,
  games: Gamepad2,
  adult: ShieldAlert,
  unclassified: CircleHelp,
}

const colorSets = [
  { icon: 'bg-sky-100/80 text-sky-700', ring: 'ring-sky-200/70' },
  { icon: 'bg-violet-100/80 text-violet-700', ring: 'ring-violet-200/70' },
  { icon: 'bg-amber-100/80 text-amber-800', ring: 'ring-amber-200/70' },
  { icon: 'bg-emerald-100/80 text-emerald-700', ring: 'ring-emerald-200/70' },
  { icon: 'bg-rose-100/80 text-rose-700', ring: 'ring-rose-200/70' },
  { icon: 'bg-indigo-100/80 text-indigo-700', ring: 'ring-indigo-200/70' },
]

export default function AppGroupForm({ groups, rules, pending, onSave }: Props) {
  const showToast = useToast()
  const [draft, setDraft] = useState(groups)
  const [name, setName] = useState('')
  const [budget, setBudget] = useState('')
  const [nameError, setNameError] = useState<string | null>(null)
  const [budgetError, setBudgetError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [confirming, setConfirming] = useState<AppGroup | null>(null)

  function openCreate() {
    setName('')
    setBudget('')
    setNameError(null)
    setBudgetError(null)
    setCreating(true)
  }

  function update(group: AppGroup, value: string) {
    const result = appGroupBudgetInputSchema.safeParse(value)
    if (!result.success) return
    setDraft(draft.map((item) => (item.id === group.id ? { ...item, budget_minutes: result.data } : item)))
  }

  function add(event: FormEvent) {
    event.preventDefault()
    const nameResult = appGroupNameSchema(draft).safeParse(name)
    const budgetResult = appGroupBudgetInputSchema.safeParse(budget)
    setNameError(nameResult.success ? null : nameResult.error.issues[0].message)
    setBudgetError(budgetResult.success ? null : budgetResult.error.issues[0].message)
    if (!nameResult.success || !budgetResult.success) {
      return
    }

    setDraft([...draft, { id: `custom_${crypto.randomUUID()}`, name: nameResult.data, budget_minutes: budgetResult.data }])
    setName('')
    setBudget('')
    setCreating(false)
  }

  function remove() {
    if (!confirming) return
    setDraft(draft.filter((item) => item.id !== confirming.id))
    setConfirming(null)
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
    <>
      <Card
        title="Ngân sách theo nhóm ứng dụng"
        description="Mỗi nhóm có bộ đếm riêng, đặt lại vào đầu ngày. Để trống để không giới hạn."
        actions={
          <Button onClick={openCreate}>
            <Plus aria-hidden="true" className="size-4" />
            Tạo nhóm
          </Button>
        }
      >
        <div className="flex flex-col gap-4">
          <div className="grid gap-3 sm:grid-cols-2">
            {draft.map((group, index) => {
              const assignedCount = rules.filter((rule) => rule.group_id === group.id).length
              const Icon = groupIcons[group.id] ?? (group.id.startsWith('custom_') ? FolderCog : Shapes)
              const colors = colorSets[index % colorSets.length]
              return (
                <article
                  key={group.id}
                  className={`glass-strong min-w-0 rounded-glass p-4 ring-1 ring-inset ${colors.ring}`}
                >
                  <header className="flex min-w-0 items-center gap-3">
                    <span className={`grid size-11 shrink-0 place-items-center rounded-2xl ${colors.icon}`}>
                      <Icon aria-hidden="true" className="size-5" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <h3 className="truncate font-semibold text-ink">{group.name}</h3>
                      <div className="mt-1.5 flex flex-wrap items-center gap-2">
                        <Badge tone={group.id.startsWith('custom_') ? 'brand' : 'neutral'}>
                          {group.id.startsWith('custom_') ? 'Tùy chỉnh' : 'Mặc định'}
                        </Badge>
                        <span className="inline-flex items-center gap-1.5 text-xs text-ink-muted">
                          <span className={`size-2 rounded-full ${assignedCount ? 'bg-brand-500' : 'bg-slate-300'}`} />
                          {assignedCount} ứng dụng
                        </span>
                      </div>
                    </div>
                    {group.id.startsWith('custom_') && (
                      <Button
                        type="button"
                        size="md"
                        variant="ghost"
                        className="min-h-10 min-w-10 shrink-0 rounded-xl bg-rose-100/90 !px-0 text-rose-700 hover:bg-rose-200/90"
                        disabled={pending || assignedCount > 0}
                        title={assignedCount > 0 ? 'Hãy chuyển ứng dụng khác trước khi xóa nhóm.' : 'Xóa nhóm'}
                        aria-label={`Xóa nhóm ${group.name}`}
                        onClick={() => setConfirming(group)}
                      >
                        <Trash2 aria-hidden="true" className="size-5" strokeWidth={2.3} />
                      </Button>
                    )}
                  </header>
                  <div className="mt-4 flex items-end gap-2">
                    <TextField
                      className="min-w-0 flex-1"
                      label="Ngân sách mỗi ngày"
                      type="number"
                      min={0}
                      max={1440}
                      value={group.budget_minutes ?? ''}
                      placeholder="Không giới hạn"
                      hint="Để trống nếu không giới hạn."
                      disabled={pending}
                      onChange={(event) => update(group, event.target.value)}
                    />
                    <span className="mb-5 grid h-11 shrink-0 place-items-center rounded-control bg-white/60 px-3 text-sm font-medium text-ink-muted">
                      Phút
                    </span>
                  </div>
                </article>
              )
            })}
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-ink-muted">Thay đổi ngân sách được lưu cùng một lần.</p>
            <Button type="button" loading={pending} disabled={pending} onClick={save}>
              <Save aria-hidden="true" className="size-4" />
              Lưu nhóm và ngân sách
            </Button>
          </div>
        </div>
      </Card>

      <Dialog
        open={creating}
        title="Tạo nhóm ứng dụng"
        onClose={() => setCreating(false)}
        actions={
          <>
            <Button variant="ghost" onClick={() => setCreating(false)}>
              Hủy
            </Button>
            <Button type="submit" form="create-app-group-form">
              <CirclePlus aria-hidden="true" className="size-4" />
              Tạo nhóm
            </Button>
          </>
        }
      >
        <form id="create-app-group-form" className="flex flex-col gap-4" onSubmit={add} noValidate>
          <TextField
            label="Tên nhóm"
            maxLength={40}
            required
            value={name}
            error={nameError}
            errorMode="inline"
            onChange={(event) => {
              setName(event.target.value)
              setNameError(null)
            }}
          />
          <div className="flex items-end gap-2">
            <TextField
              className="min-w-0 flex-1"
              label="Ngân sách mỗi ngày"
              type="number"
              min={0}
              max={1440}
              value={budget}
              placeholder="Không giới hạn"
              hint="Để trống nếu không giới hạn."
              error={budgetError}
              errorMode="inline"
              onChange={(event) => {
                setBudget(event.target.value)
                setBudgetError(null)
              }}
            />
            <span className="mb-5 grid h-11 shrink-0 place-items-center rounded-control bg-white/60 px-3 text-sm font-medium text-ink-muted">
              Phút
            </span>
          </div>
        </form>
      </Dialog>

      <Dialog
        open={confirming !== null}
        title={`Xóa nhóm ${confirming?.name ?? ''}?`}
        onClose={() => setConfirming(null)}
        actions={
          <>
            <Button variant="ghost" onClick={() => setConfirming(null)}>
              Hủy
            </Button>
            <Button variant="danger" onClick={remove}>
              <Trash2 aria-hidden="true" className="size-4" />
              Xóa nhóm
            </Button>
          </>
        }
      >
        Nhóm sẽ bị xóa khỏi danh sách ngân sách. Thao tác chưa được áp dụng cho thiết bị cho đến khi bạn lưu thay đổi.
      </Dialog>
    </>
  )
}
