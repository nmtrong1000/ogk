import { useState, type ChangeEvent, type FormEvent } from 'react'
import { Button, Select, TextField } from '@/shared/components/index.ts'
import { useToast } from '@/shared/components/ToastContext.ts'
import type { AppGroup, AppRule, AppRuleAction } from '@/shared/types/policy.ts'
import { ACTION_LABELS } from '@/features/appcontrol/utils/messages.ts'
import { canHash, sha256File } from '@/features/appcontrol/utils/sha256.ts'
import { appRuleFormSchema } from '@/features/appcontrol/schemas.ts'

type Props = {
  rules: AppRule[]
  groups: AppGroup[]
  pending: boolean
  onAdd: (rule: AppRule) => void
}

export default function AppRuleForm({ rules, groups, pending, onAdd }: Props) {
  const showToast = useToast()
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
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField
          label="Tên tệp chạy"
          hint="Ví dụ: game.exe"
          required
          value={name}
          maxLength={255}
          onChange={(e) => setName(e.target.value)}
        />
        <Select
          label="Hành động"
          value={action}
          options={[
            { value: 'block', label: ACTION_LABELS.block },
            { value: 'allow', label: ACTION_LABELS.allow },
          ]}
          hint={
            action === 'allow'
              ? 'Cho phép chỉ có tác dụng khi có mã SHA-256: đúng bản tệp đó được chạy dù tên bị chặn.'
              : 'Chặn theo tên, và theo mã SHA-256 nếu có, nên đổi tên tệp vẫn bị chặn.'
          }
          onChange={(e) => setAction(e.target.value as AppRuleAction)}
        />
      </div>
      <Select
        label="Nhóm ứng dụng"
        required
        value={groupId}
        options={groups.map((group) => ({ value: group.id, label: group.name }))}
        hint="Thời gian ứng dụng được tính vào ngân sách của nhóm này."
        onChange={(event) => setGroupId(event.target.value)}
      />
      <TextField
        label="Mã SHA-256 (không bắt buộc)"
        hint="64 ký tự. Có thể chọn tệp bên dưới để tính tự động; tệp không được tải lên."
        value={sha}
        maxLength={64}
        spellCheck={false}
        onChange={(e) => setSha(e.target.value.trim())}
      />
      {canHash() && (
        <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">
          Chọn tệp để tính SHA-256
          <input
            type="file"
            accept=".exe"
            disabled={hashing}
            onChange={pickFile}
            className="text-sm text-ink-muted file:mr-3 file:rounded-control file:border-0 file:bg-brand-100 file:px-3 file:py-2 file:text-brand-800"
          />
          {hashing && <span className="text-ink-muted">Đang tính…</span>}
        </label>
      )}
      <div className="flex justify-end">
        <Button type="submit" loading={pending} disabled={hashing}>
          Thêm luật
        </Button>
      </div>
    </form>
  )
}
