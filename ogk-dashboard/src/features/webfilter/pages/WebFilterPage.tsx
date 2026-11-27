import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type KeyboardEvent } from 'react'
import { useParams } from 'react-router-dom'
import {
  ArrowLeftRight,
  BookOpen,
  Check,
  CircleHelp,
  Film,
  Gamepad2,
  Globe,
  MessageCircle,
  Pencil,
  Plus,
  ShieldAlert,
  Trash2,
  X,
} from 'lucide-react'
import { z } from 'zod'
import { ApiError } from '@/shared/api/client.ts'
import {
  getPolicyChild,
  policyChildKey,
  policyKey,
  policyVersionsKey,
  getPolicy,
  updatePolicy,
} from '@/shared/api/policy.ts'
import { Alert, Badge, Button, Card, ChildPageHeader, Spinner } from '@/shared/components/index.ts'
import { useToast } from '@/shared/components/ToastContext.ts'
import type { Policy } from '@/shared/types/policy.ts'
import { WEB_CATEGORIES, type WebCategory } from '@/features/webfilter/api.ts'

type DomainListKey = 'web_blocklist' | 'web_allowlist'
type DomainEditor = { list: DomainListKey; domain: string | null; draft: string } | null

const categoryDetails: Record<WebCategory, { name: string; detail: string; icon: typeof Globe }> = {
  education: { name: 'Giáo dục', detail: 'Học tập, tra cứu và nội dung giáo dục.', icon: BookOpen },
  entertainment: { name: 'Giải trí', detail: 'Video, phim ảnh và nội dung thư giãn.', icon: Film },
  social: { name: 'Mạng xã hội', detail: 'Mạng xã hội và nền tảng giao tiếp.', icon: MessageCircle },
  games: { name: 'Trò chơi', detail: 'Website chơi game và trò chơi trực tuyến.', icon: Gamepad2 },
  adult: { name: 'Không phù hợp lứa tuổi', detail: 'Nội dung người lớn và nhạy cảm.', icon: ShieldAlert },
  unclassified: { name: 'Chưa phân loại', detail: 'Website chưa được xếp vào nhóm khác.', icon: CircleHelp },
}

const domainSchema = z
  .string()
  .trim()
  .toLowerCase()
  .regex(/^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/, 'Nhập tên miền hợp lệ, ví dụ example.com.')

function DomainColumn({
  list,
  title,
  description,
  domains,
  selectedDomain,
  editor,
  disabled,
  onSelect,
  onAddClick,
  onDraftChange,
  onSave,
  onCancel,
  onEdit,
  onRemove,
}: {
  list: DomainListKey
  title: string
  description: string
  domains: string[]
  selectedDomain: string | null
  editor: DomainEditor
  disabled: boolean
  onSelect: (domain: string) => void
  onAddClick: () => void
  onDraftChange: (value: string) => void
  onSave: () => void
  onCancel: () => void
  onEdit: (domain: string) => void
  onRemove: (domain: string) => void
}) {
  const blocking = list === 'web_blocklist'
  const renderEditor = (key: string) => (
    <li key={key} className="flex min-w-0 items-center gap-1.5 rounded-control bg-white/70 p-1.5 ring-1 ring-inset ring-brand-200/70">
      <Globe aria-hidden="true" className="ml-2 size-4 shrink-0 text-brand-600" />
      <input
        aria-label="Tên miền"
        autoFocus
        className="glass-input h-10 min-w-0 flex-1 rounded-control px-2.5 text-sm text-ink outline-none transition focus:border-brand-400 focus:ring-4 focus:ring-brand-200/60"
        placeholder="example.com"
        value={editor?.draft ?? ''}
        disabled={disabled}
        onChange={(event) => onDraftChange(event.target.value)}
        onKeyDown={(event: KeyboardEvent<HTMLInputElement>) => {
          if (event.key === 'Enter') {
            event.preventDefault()
            onSave()
          }
          if (event.key === 'Escape') onCancel()
        }}
      />
      <Button type="button" size="sm" variant="ghost" aria-label="Lưu tên miền" title="Lưu" disabled={disabled} onClick={onSave}>
        <Check aria-hidden="true" className="size-4" />
      </Button>
      <Button type="button" size="sm" variant="ghost" aria-label="Hủy chỉnh sửa" title="Hủy" disabled={disabled} onClick={onCancel}>
        <X aria-hidden="true" className="size-4" />
      </Button>
    </li>
  )
  return (
    <section
      className={`glass-strong min-w-0 rounded-glass p-4 ring-1 ring-inset sm:p-5 ${blocking ? 'ring-rose-200/70' : 'ring-emerald-200/70'}`}
    >
      <header className="flex items-center gap-3">
        <span
          className={`grid size-11 shrink-0 place-items-center rounded-2xl ${blocking ? 'bg-rose-100/80 text-rose-700' : 'bg-emerald-100/80 text-emerald-700'}`}
        >
          <Globe aria-hidden="true" className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold text-ink">{title}</h3>
            <Badge tone={blocking ? 'danger' : 'success'}>{domains.length}</Badge>
          </div>
          <p className="mt-0.5 text-xs text-ink-muted">{description}</p>
        </div>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={disabled}
          aria-label={`Thêm tên miền vào ${title.toLowerCase()}`}
          title="Thêm tên miền"
          onClick={onAddClick}
        >
          <Plus aria-hidden="true" className="size-4" />
          <span className="hidden sm:inline">Thêm</span>
        </Button>
      </header>

      <ul className="mt-4 flex min-h-28 flex-col gap-2">
        {editor?.list === list && editor.domain === null && renderEditor('new-domain')}
        {domains.map((domain) => {
          const selected = domain === selectedDomain
          if (editor?.list === list && editor.domain === domain) return renderEditor(domain)
          return (
            <li key={domain} className="flex min-w-0 items-center gap-1.5">
              <button
                type="button"
                aria-pressed={selected}
                onClick={() => onSelect(domain)}
                className={`flex min-h-11 min-w-0 flex-1 cursor-pointer items-center gap-2.5 rounded-control px-3 text-left text-sm transition duration-150 hover:-translate-y-0.5 hover:shadow-control ${selected ? 'bg-brand-100/90 text-brand-800 ring-1 ring-inset ring-brand-300/80' : 'glass-input text-ink hover:bg-white/85'}`}
              >
                <Globe aria-hidden="true" className="size-4 shrink-0 text-brand-600" />
                <span className="min-w-0 flex-1 truncate font-medium" title={domain}>
                  {domain}
                </span>
                {selected && <Check aria-hidden="true" className="size-4 shrink-0" />}
              </button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                disabled={disabled}
                aria-label={`Sửa ${domain}`}
                title="Sửa tên miền"
                className="shrink-0 text-brand-700 hover:bg-brand-50/80"
                onClick={() => onEdit(domain)}
              >
                <Pencil aria-hidden="true" className="size-4" />
              </Button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                disabled={disabled}
                aria-label={`Xóa ${domain}`}
                title="Xóa tên miền"
                className="shrink-0 text-rose-700 hover:bg-rose-50/80"
                onClick={() => onRemove(domain)}
              >
                <Trash2 aria-hidden="true" className="size-4" />
              </Button>
            </li>
          )
        })}
        {domains.length === 0 && !(editor?.list === list && editor.domain === null) && (
          <li className="grid flex-1 place-items-center rounded-control bg-white/45 px-4 py-5 text-center text-sm text-ink-muted">
            Chưa có tên miền
          </li>
        )}
      </ul>
    </section>
  )
}

export default function WebFilterPage() {
  const id = Number(useParams().id)
  const client = useQueryClient()
  const showToast = useToast()
  const child = useQuery({ queryKey: policyChildKey(id), queryFn: () => getPolicyChild(id) })
  const policy = useQuery({ queryKey: policyKey(id), queryFn: () => getPolicy(id) })
  const [domainEditor, setDomainEditor] = useState<DomainEditor>(null)
  const [selected, setSelected] = useState<{ list: DomainListKey; domain: string } | null>(null)
  const save = useMutation({
    mutationFn: (body: Partial<Policy>) => updatePolicy(id, body),
    onSuccess: (value) => {
      client.setQueryData(policyKey(id), value)
      client.invalidateQueries({ queryKey: policyVersionsKey(id) })
    },
  })
  if (!Number.isInteger(id) || id < 1) return <Alert tone="error">Không tìm thấy trẻ.</Alert>
  if (child.isPending || policy.isPending)
    return (
      <div className="grid place-items-center py-20">
        <Spinner size="lg" />
      </div>
    )
  if (policy.error instanceof ApiError && policy.error.status === 404)
    return <Alert tone="error">Không tìm thấy trẻ.</Alert>
  if (policy.isError) return <Alert tone="error">Không tải được chính sách lọc web.</Alert>

  const current = policy.data
  const toggleCategory = (category: WebCategory) => {
    save.mutate({
      blocked_categories: current.blocked_categories.includes(category)
        ? current.blocked_categories.filter((item) => item !== category)
        : [...current.blocked_categories, category],
    })
  }

  const saveDomain = async () => {
    if (!domainEditor) return
    const { list, domain: originalDomain } = domainEditor
    const normalized = domainEditor.draft.trim().replace(/\.+$/, '')
    const result = domainSchema.safeParse(normalized)
    if (!result.success) {
      showToast({ tone: 'error', message: result.error.issues[0].message })
      return
    }
    const otherList: DomainListKey = list === 'web_blocklist' ? 'web_allowlist' : 'web_blocklist'
    if (result.data === originalDomain) {
      setDomainEditor(null)
      return
    }
    if (current[list].includes(result.data)) {
      showToast({ tone: 'info', message: 'Tên miền đã có trong danh sách này.' })
      return
    }
    if (current[otherList].includes(result.data)) {
      showToast({ tone: 'info', message: 'Tên miền đã ở cột bên kia. Hãy chọn tên miền rồi chuyển danh sách.' })
      return
    }

    const updatedDomains = originalDomain
      ? current[list].map((domain) => (domain === originalDomain ? result.data : domain))
      : [...current[list], result.data]
    try {
      await save.mutateAsync(list === 'web_blocklist' ? { web_blocklist: updatedDomains } : { web_allowlist: updatedDomains })
      if (selected?.list === list && selected.domain === originalDomain) setSelected(null)
      setDomainEditor(null)
    } catch {}
  }

  const removeDomain = (list: DomainListKey, domain: string) => {
    if (selected?.list === list && selected.domain === domain) setSelected(null)
    if (list === 'web_blocklist') {
      save.mutate({ web_blocklist: current.web_blocklist.filter((item) => item !== domain) })
    } else {
      save.mutate({ web_allowlist: current.web_allowlist.filter((item) => item !== domain) })
    }
  }

  const transferSelected = () => {
    if (!selected) return
    const target: DomainListKey = selected.list === 'web_blocklist' ? 'web_allowlist' : 'web_blocklist'
    const sourceDomains = current[selected.list].filter((domain) => domain !== selected.domain)
    const targetDomains = current[target].includes(selected.domain)
      ? current[target]
      : [...current[target], selected.domain]
    if (selected.list === 'web_blocklist') {
      save.mutate({ web_blocklist: sourceDomains, web_allowlist: targetDomains })
    } else {
      save.mutate({ web_allowlist: sourceDomains, web_blocklist: targetDomains })
    }
    setSelected(null)
  }

  const openAdd = (list: DomainListKey) => setDomainEditor({ list, domain: null, draft: '' })
  const openEdit = (list: DomainListKey, domain: string) => setDomainEditor({ list, domain, draft: domain })

  const blockSelected = selected?.list === 'web_blocklist'
  return (
    <div className="flex flex-col gap-6">
      <ChildPageHeader
        title="Lọc website"
        description="Chặn nhóm nội dung và quản lý ngoại lệ tên miền cho trẻ. Tên miền miễn chặn luôn được ưu tiên hơn tên miền bị chặn."
        icon={Globe}
      />
      {save.error && <Alert tone="error">Không lưu được luật website.</Alert>}
      <Card title="Nhóm bị chặn" description="Chọn loại nội dung không phù hợp với trẻ. Các lựa chọn được áp dụng cho mọi website thuộc nhóm.">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <Badge tone={current.blocked_categories.length ? 'danger' : 'neutral'}>
            {current.blocked_categories.length} nhóm đang chặn
          </Badge>
          <span className="text-sm text-ink-muted">Nhấn vào thẻ để bật hoặc tắt.</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {WEB_CATEGORIES.map((category) => {
            const detail = categoryDetails[category]
            const Icon = detail.icon
            const checked = current.blocked_categories.includes(category)
            return (
              <label
                key={category}
                className={`flex min-h-24 cursor-pointer items-center gap-3 rounded-glass p-4 transition duration-150 hover:-translate-y-0.5 hover:shadow-control focus-within:ring-4 focus-within:ring-brand-200/70 ${checked ? 'bg-rose-50/85 ring-1 ring-inset ring-rose-200/80' : 'glass-strong ring-1 ring-inset ring-brand-100/70 hover:bg-white/85'}`}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={save.isPending}
                  onChange={() => toggleCategory(category)}
                  className="size-4.5 shrink-0 cursor-pointer accent-rose-600"
                />
                <span
                  className={`grid size-11 shrink-0 place-items-center rounded-2xl ${checked ? 'bg-rose-100 text-rose-700' : 'bg-brand-100/80 text-brand-700'}`}
                >
                  <Icon aria-hidden="true" className="size-5" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block font-semibold text-ink">{detail.name}</span>
                  <span className="mt-0.5 block text-xs leading-relaxed text-ink-muted">{detail.detail}</span>
                </span>
                {checked && <Check aria-hidden="true" className="size-4 shrink-0 text-rose-600" />}
              </label>
            )
          })}
        </div>
      </Card>

      <Card title="Tên miền riêng" description="Tên miền và tên miền con cùng chịu luật. Ví dụ example.com áp dụng cả a.example.com.">
        <div className="web-domain-grid">
          <DomainColumn
            list="web_blocklist"
            title="Danh sách chặn"
            description="Luôn chặn website thuộc danh sách này."
            domains={current.web_blocklist}
            selectedDomain={selected?.list === 'web_blocklist' ? selected.domain : null}
            editor={domainEditor?.list === 'web_blocklist' ? domainEditor : null}
            disabled={save.isPending}
            onSelect={(domain) => setSelected({ list: 'web_blocklist', domain })}
            onAddClick={() => openAdd('web_blocklist')}
            onDraftChange={(draft) => setDomainEditor((value) => (value ? { ...value, draft } : value))}
            onSave={saveDomain}
            onCancel={() => setDomainEditor(null)}
            onEdit={(domain) => openEdit('web_blocklist', domain)}
            onRemove={(domain) => removeDomain('web_blocklist', domain)}
          />
          <div className="flex items-center justify-center">
            <Button
              type="button"
              variant="secondary"
              disabled={!selected || save.isPending}
              title={selected ? (blockSelected ? 'Chuyển sang danh sách cho phép' : 'Chuyển sang danh sách chặn') : 'Chọn một tên miền để chuyển'}
              onClick={transferSelected}
            >
              <ArrowLeftRight aria-hidden="true" className="size-4" />
              {selected ? (blockSelected ? 'Cho phép' : 'Chặn') : 'Chuyển'}
            </Button>
          </div>
          <DomainColumn
            list="web_allowlist"
            title="Danh sách cho phép"
            description="Cho phép website dù nhóm nội dung đang bị chặn."
            domains={current.web_allowlist}
            selectedDomain={selected?.list === 'web_allowlist' ? selected.domain : null}
            editor={domainEditor?.list === 'web_allowlist' ? domainEditor : null}
            disabled={save.isPending}
            onSelect={(domain) => setSelected({ list: 'web_allowlist', domain })}
            onAddClick={() => openAdd('web_allowlist')}
            onDraftChange={(draft) => setDomainEditor((value) => (value ? { ...value, draft } : value))}
            onSave={saveDomain}
            onCancel={() => setDomainEditor(null)}
            onEdit={(domain) => openEdit('web_allowlist', domain)}
            onRemove={(domain) => removeDomain('web_allowlist', domain)}
          />
        </div>
      </Card>
    </div>
  )
}
