import { useState, type ChangeEvent, type FormEvent } from 'react'
import { Alert, Button, Select, TextField } from '@/shared/components/index.ts'
import type { AppRule, AppRuleAction } from '@/shared/types/policy.ts'
import {
  ACTION_LABELS,
  DUPLICATE_ERROR,
  LIMIT_ERROR,
  MAX_APP_RULES,
  NAME_ERROR,
  SHA_ERROR,
} from '@/features/appcontrol/utils/messages.ts'
import { canHash, sha256File } from '@/features/appcontrol/utils/sha256.ts'

type Props = {
  rules: AppRule[]
  pending: boolean
  onAdd: (rule: AppRule) => void
}

const SHA_PATTERN = /^[0-9a-f]{64}$/

function normalizeName(value: string): string | null {
  const name = value.trim().toLowerCase()
  return name.length > 0 && name.length <= 255 && !/[\\/]/.test(name) ? name : null
}

export default function AppRuleForm({ rules, pending, onAdd }: Props) {
  const [name, setName] = useState('')
  const [sha, setSha] = useState('')
  const [action, setAction] = useState<AppRuleAction>('block')
  const [errors, setErrors] = useState<{ name?: string; sha?: string; form?: string }>({})
  const [hashing, setHashing] = useState(false)

  async function pickFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setHashing(true)
    try {
      setSha(await sha256File(file))
      if (!name.trim()) setName(file.name.toLowerCase())
      setErrors({})
    } catch {
      setErrors({ sha: 'Không đọc được tệp này để tính SHA-256.' })
    } finally {
      setHashing(false)
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    const normalized = normalizeName(name)
    const digest = sha.trim().toLowerCase()
    const next: typeof errors = {}
    if (normalized === null) next.name = NAME_ERROR
    if (digest && !SHA_PATTERN.test(digest)) next.sha = SHA_ERROR
    const sha256 = digest || null
    if (!next.name && !next.sha) {
      if (rules.length >= MAX_APP_RULES) next.form = LIMIT_ERROR
      else if (rules.some((r) => r.name === normalized && r.sha256 === sha256)) next.form = DUPLICATE_ERROR
    }
    setErrors(next)
    if (next.name || next.sha || next.form || normalized === null) return
    onAdd({ name: normalized, sha256, action })
    setName('')
    setSha('')
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
      {errors.form && <Alert tone="error">{errors.form}</Alert>}
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField
          label="Tên tệp chạy"
          hint="Ví dụ: game.exe"
          value={name}
          maxLength={255}
          error={errors.name}
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
      <TextField
        label="Mã SHA-256 (không bắt buộc)"
        hint="64 ký tự. Có thể chọn tệp bên dưới để tính tự động; tệp không được tải lên."
        value={sha}
        maxLength={64}
        spellCheck={false}
        error={errors.sha}
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
