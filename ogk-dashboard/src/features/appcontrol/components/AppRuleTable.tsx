import { useState } from 'react'
import { AppWindow, Ban, CircleCheck, Fingerprint, Trash2 } from 'lucide-react'
import { Badge, Button, Dialog, Select } from '@/shared/components/index.ts'
import type { AppGroup, AppRule } from '@/shared/types/policy.ts'
import { ACTION_LABELS } from '@/features/appcontrol/utils/messages.ts'

type Props = {
  rules: AppRule[]
  groups: AppGroup[]
  pending: boolean
  onRemove: (rule: AppRule) => void
  onAssign: (rule: AppRule, groupId: string) => void
}

function shortSha(sha: string | null): string {
  return sha ? `${sha.slice(0, 8)}…${sha.slice(-8)}` : 'Không có'
}

export default function AppRuleTable({ rules, groups, pending, onRemove, onAssign }: Props) {
  const [confirming, setConfirming] = useState<AppRule | null>(null)

  function remove() {
    if (!confirming) return
    onRemove(confirming)
    setConfirming(null)
  }

  if (rules.length === 0) {
    return (
      <div className="glass-input flex flex-col items-center gap-3 rounded-glass px-5 py-10 text-center">
        <span className="grid size-14 place-items-center rounded-2xl bg-brand-100/80 text-brand-700">
          <AppWindow aria-hidden="true" className="size-7" />
        </span>
        <div>
          <p className="font-semibold text-ink">Chưa có luật ứng dụng</p>
          <p className="mt-1 text-sm text-ink-muted">Mọi ứng dụng đều được chạy. Thêm luật nếu muốn chặn hoặc phân nhóm.</p>
        </div>
      </div>
    )
  }
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="brand">{rules.length} luật</Badge>
        <Badge tone="danger">{rules.filter((rule) => rule.action === 'block').length} bị chặn</Badge>
        <Badge tone="success">{rules.filter((rule) => rule.action === 'allow').length} được phép</Badge>
      </div>
      <div className="grid gap-3 xl:grid-cols-2">
        {rules.map((rule) => (
          <article
            key={`${rule.name}-${rule.sha256 ?? ''}`}
            className={`glass-strong min-w-0 rounded-glass p-4 ring-1 ring-inset ${rule.action === 'block' ? 'ring-rose-200/70' : 'ring-emerald-200/70'}`}
          >
            <header className="flex min-w-0 items-start gap-3">
              <span
                className={`grid size-11 shrink-0 place-items-center rounded-2xl ${rule.action === 'block' ? 'bg-rose-100/80 text-rose-700' : 'bg-emerald-100/80 text-emerald-700'}`}
              >
                {rule.action === 'block' ? (
                  <Ban aria-hidden="true" className="size-5" />
                ) : (
                  <CircleCheck aria-hidden="true" className="size-5" />
                )}
              </span>
              <div className="min-w-0 flex-1">
                <h3 className="break-all font-semibold text-ink" title={rule.name}>
                  {rule.name}
                </h3>
                <div className="mt-1.5 flex flex-wrap items-center gap-2">
                  <Badge tone={rule.action === 'block' ? 'danger' : 'success'}>{ACTION_LABELS[rule.action]}</Badge>
                  <span className="text-xs text-ink-muted">
                    {rule.sha256 ? 'Khớp tên tệp và mã SHA-256' : 'Khớp theo tên tệp'}
                  </span>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                disabled={pending}
                className="shrink-0 text-rose-700 hover:bg-rose-50/80"
                onClick={() => setConfirming(rule)}
              >
                <Trash2 aria-hidden="true" className="size-4" />
                Xóa
              </Button>
            </header>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="min-w-0 rounded-control bg-white/55 p-3">
                <p className="flex items-center gap-1.5 text-xs font-medium text-ink-muted">
                  <Fingerprint aria-hidden="true" className="size-4" />
                  Mã SHA-256
                </p>
                <p className="mt-1 truncate font-mono text-sm text-ink" title={rule.sha256 ?? undefined}>
                  {shortSha(rule.sha256)}
                </p>
              </div>
              <div className="min-w-0 rounded-control bg-white/55 p-3">
                <Select
                  label="Nhóm tính thời gian"
                  aria-label={`Nhóm của ${rule.name}`}
                  value={rule.group_id}
                  disabled={pending}
                  options={groups.map((group) => ({ value: group.id, label: group.name }))}
                  onChange={(event) => onAssign(rule, event.target.value)}
                />
              </div>
            </div>
          </article>
        ))}
      </div>
      <Dialog
        open={confirming !== null}
        title={`Xóa luật cho ${confirming?.name ?? 'ứng dụng'}?`}
        onClose={() => !pending && setConfirming(null)}
        actions={
          <>
            <Button variant="ghost" disabled={pending} onClick={() => setConfirming(null)}>
              Hủy
            </Button>
            <Button variant="danger" loading={pending} onClick={remove}>
              <Trash2 aria-hidden="true" className="size-4" />
              Xóa luật
            </Button>
          </>
        }
      >
        Bạn có chắc muốn xóa luật chặn/cho phép cho <strong className="font-semibold text-ink">{confirming?.name}</strong>?
      </Dialog>
    </div>
  )
}
