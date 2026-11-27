import { useId, useState, type ChangeEvent, type FormEvent } from 'react'
import { AppWindow, ArrowUpRight, Ban, CircleCheck, Fingerprint, FolderOpen, Plus, Upload } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button, Select, TextField } from '@/shared/components/index.ts'
import { useToast } from '@/shared/components/ToastContext.ts'
import type { AppGroup, AppRule, AppRuleAction } from '@/shared/types/policy.ts'
import { ACTION_LABELS } from '@/features/appcontrol/utils/messages.ts'
import { canHash, sha256File } from '@/features/appcontrol/utils/sha256.ts'
import { appRuleFormSchema } from '@/features/appcontrol/schemas.ts'

type Props = {
  rules: AppRule[]
  groups: AppGroup[]
  childId: number
  pending: boolean
  onAdd: (rule: AppRule) => void
}

export default function AppRuleForm({ rules, groups, childId, pending, onAdd }: Props) {
  const showToast = useToast()
  const fileInputId = useId()
  const [name, setName] = useState('')
  const [sha, setSha] = useState('')
  const [action, setAction] = useState<AppRuleAction>('block')
  const [groupId, setGroupId] = useState('unclassified')
  const [hashing, setHashing] = useState(false)

  async function pickFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setHashing(true)
    try {
      setSha(await sha256File(file))
      if (!name.trim()) setName(file.name.toLowerCase())
    } catch {
      showToast({ tone: 'error', message: 'Không đọc được tệp này để tính SHA-256.' })
    } finally {
      setHashing(false)
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    const result = appRuleFormSchema(rules, groups).safeParse({ name, sha, action, groupId })
    if (!result.success) {
      showToast({ tone: 'error', message: result.error.issues[0].message })
      return
    }
    onAdd(result.data)
    setName('')
    setSha('')
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="glass-strong rounded-glass p-4 sm:p-5">
          <header className="mb-4 flex items-center gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-brand-100/80 text-brand-700">
              <AppWindow aria-hidden="true" className="size-5" />
            </span>
            <div>
              <h3 className="font-semibold text-ink">Thông tin ứng dụng</h3>
              <p className="text-sm text-ink-muted">Nhập tên tệp hoặc định danh chính xác ứng dụng.</p>
            </div>
          </header>
          <div className="flex flex-col gap-4">
            <TextField
              label="Tên tệp chạy"
              hint="Ví dụ: game.exe"
              required
              value={name}
              maxLength={255}
              onChange={(e) => setName(e.target.value)}
            />
            <TextField
              label="Mã SHA-256 (không bắt buộc)"
              hint="Dùng mã này để nhận diện đúng phiên bản tệp."
              value={sha}
              maxLength={64}
              spellCheck={false}
              onChange={(e) => setSha(e.target.value.trim())}
            />
            {canHash() && (
              <div className="glass-input rounded-control p-3.5">
                <input
                  id={fileInputId}
                  type="file"
                  accept=".exe"
                  disabled={hashing}
                  onChange={pickFile}
                  className="sr-only"
                />
                <label htmlFor={fileInputId} className="flex cursor-pointer items-center gap-3">
                  <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-white/70 text-brand-700">
                    <Upload aria-hidden="true" className="size-5" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold text-ink">Tính SHA-256 từ tệp</span>
                    <span className="block text-xs text-ink-muted">Tệp .exe được xử lý trên máy, không tải lên.</span>
                  </span>
                  <span className="text-sm font-semibold text-brand-700">Chọn tệp</span>
                </label>
                {hashing && <p className="mt-2 text-sm text-ink-muted">Đang tính mã SHA-256…</p>}
              </div>
            )}
          </div>
        </section>

        <section className="glass-strong rounded-glass p-4 sm:p-5">
          <header className="mb-4 flex items-center gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-violet-100/80 text-violet-700">
              <FolderOpen aria-hidden="true" className="size-5" />
            </span>
            <div>
              <h3 className="font-semibold text-ink">Cách áp dụng</h3>
              <p className="text-sm text-ink-muted">Chọn hành động và nhóm tính thời gian.</p>
            </div>
          </header>
          <fieldset>
            <legend className="mb-2 text-sm font-medium text-ink">Hành động</legend>
            <div className="grid gap-2 sm:grid-cols-2">
              <button
                type="button"
                aria-pressed={action === 'block'}
                onClick={() => setAction('block')}
                className={`flex min-h-14 cursor-pointer items-center gap-3 rounded-control px-3 py-2.5 text-left transition duration-150 hover:-translate-y-0.5 hover:shadow-control active:translate-y-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 ${action === 'block' ? 'bg-rose-100/90 text-rose-800 ring-1 ring-inset ring-rose-300/80 hover:bg-rose-200/90' : 'glass-input text-ink-muted hover:bg-white/80'}`}
              >
                <Ban aria-hidden="true" className="size-5 shrink-0" />
                <span>
                  <span className="block text-sm font-semibold">{ACTION_LABELS.block}</span>
                  <span className="block text-xs opacity-80">Ngăn ứng dụng chạy</span>
                </span>
              </button>
              <button
                type="button"
                aria-pressed={action === 'allow'}
                onClick={() => setAction('allow')}
                className={`flex min-h-14 cursor-pointer items-center gap-3 rounded-control px-3 py-2.5 text-left transition duration-150 hover:-translate-y-0.5 hover:shadow-control active:translate-y-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 ${action === 'allow' ? 'bg-emerald-100/90 text-emerald-800 ring-1 ring-inset ring-emerald-300/80 hover:bg-emerald-200/90' : 'glass-input text-ink-muted hover:bg-white/80'}`}
              >
                <CircleCheck aria-hidden="true" className="size-5 shrink-0" />
                <span>
                  <span className="block text-sm font-semibold">{ACTION_LABELS.allow}</span>
                  <span className="block text-xs opacity-80">Cho phép đúng bản tệp</span>
                </span>
              </button>
            </div>
          </fieldset>
          <div className="mt-4">
            <Select
              label="Nhóm ứng dụng"
              required
              value={groupId}
              options={groups.map((group) => ({ value: group.id, label: group.name }))}
              hint="Thời gian dùng ứng dụng được tính vào ngân sách nhóm này."
              onChange={(event) => setGroupId(event.target.value)}
            />
            <Link
              to={`/children/${childId}/screentime`}
              className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-brand-700 no-underline hover:underline"
            >
              Tạo nhóm ứng dụng
              <ArrowUpRight aria-hidden="true" className="size-3.5" />
            </Link>
          </div>
          <p className="mt-3 rounded-control bg-white/50 px-3 py-2 text-xs leading-relaxed text-ink-muted">
            {action === 'allow'
              ? 'Luật cho phép cần mã SHA-256; chỉ đúng phiên bản tệp đó được chạy dù tên bị chặn.'
              : 'Luật chặn áp dụng theo tên tệp; thêm SHA-256 để vẫn nhận diện được khi tệp bị đổi tên.'}
          </p>
        </section>
      </div>
      <div className="flex flex-col-reverse gap-3 border-t border-brand-100/80 pt-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-ink-muted">Luật mới có hiệu lực sau lần đồng bộ kế tiếp của máy.</p>
        <Button type="submit" loading={pending} disabled={hashing}>
          <Plus aria-hidden="true" className="size-4" />
          Thêm luật
        </Button>
      </div>
    </form>
  )
}
