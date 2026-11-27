import { useMemo, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CircleHelp, Globe2, Pencil, Plus, Tags, Trash2 } from 'lucide-react'
import { ApiError } from '@/shared/api/client.ts'
import {
  Alert,
  Badge,
  Button,
  Card,
  Dialog,
  EmptyState,
  Pagination,
  Select,
  Spinner,
  Table,
  TableBody,
  TableHead,
  TableRow,
  Td,
  TextField,
  Th,
} from '@/shared/components/index.ts'
import { useToast } from '@/shared/components/ToastContext.ts'
import { formatDateTime } from '@/shared/utils/dateTime.ts'
import {
  getCatalog,
  updateCatalog,
  WEB_CATEGORIES,
  type CatalogEntry,
  type WebCategory,
} from '@/features/webfilter/api.ts'
import { catalogFormSchema } from '@/features/webfilter/schemas.ts'

const CATEGORY_LABELS: Record<WebCategory, string> = {
  education: 'Giáo dục',
  entertainment: 'Giải trí',
  social: 'Mạng xã hội',
  games: 'Trò chơi',
  adult: 'Không phù hợp lứa tuổi',
  unclassified: 'Chưa phân loại',
}

const CATEGORY_TONES: Record<WebCategory, 'neutral' | 'brand' | 'success' | 'warning' | 'danger'> = {
  education: 'success',
  entertainment: 'warning',
  social: 'brand',
  games: 'warning',
  adult: 'danger',
  unclassified: 'neutral',
}

const PAGE_SIZE = 20

type SaveAction = 'add' | 'update' | 'delete'
type SaveInput = { domain: string; category: WebCategory | null; action: SaveAction }

function saveErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === 'invalid_domain') return 'Tên miền không hợp lệ.'
    if (error.code === 'invalid_category') return 'Nhóm phân loại không hợp lệ.'
    if (error.code === 'catalog_minimum_size') return 'Không thể xóa thêm vì danh mục cần giữ ít nhất 200 tên miền.'
    if (error.code === 'catalog_maximum_size') return 'Danh mục đã đạt giới hạn 1.000 tên miền.'
    if (error.code === 'not_found') return 'Tên miền không còn trong bảng phân loại.'
  }
  return 'Không lưu được thay đổi. Vui lòng thử lại.'
}

function Metric({
  label,
  value,
  icon: Icon,
  tone,
}: {
  label: string
  value: number
  icon: typeof Globe2
  tone: string
}) {
  return (
    <div className="glass-strong flex min-w-0 items-center gap-3 rounded-glass p-4 ring-1 ring-inset ring-white/70">
      <span className={`grid size-11 shrink-0 place-items-center rounded-2xl ${tone}`}>
        <Icon aria-hidden="true" className="size-5" />
      </span>
      <div className="min-w-0">
        <p className="text-xs font-medium text-ink-muted">{label}</p>
        <p className="text-xl font-bold text-ink">{value}</p>
      </div>
    </div>
  )
}

export default function AdminCatalogPage() {
  const client = useQueryClient()
  const showToast = useToast()
  const catalog = useQuery({ queryKey: ['admin', 'webfilter', 'catalog'], queryFn: getCatalog })
  const [domain, setDomain] = useState('')
  const [category, setCategory] = useState<WebCategory>('unclassified')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<CatalogEntry | null>(null)
  const [editCategory, setEditCategory] = useState<WebCategory>('unclassified')
  const [removingDomain, setRemovingDomain] = useState<string | null>(null)
  const save = useMutation({
    mutationFn: ({ domain: name, category: group }: SaveInput) => updateCatalog(name, group),
    onSuccess: async (_result, variables) => {
      if (variables.action === 'add') {
        setDomain('')
        setPage(1)
        showToast({ tone: 'success', message: `Đã thêm ${variables.domain} vào bảng phân loại.` })
      } else if (variables.action === 'update') {
        setEditing(null)
        showToast({ tone: 'success', message: `Đã cập nhật phân loại cho ${variables.domain}.` })
      } else {
        setRemovingDomain(null)
        showToast({ tone: 'success', message: `Đã xóa ${variables.domain} khỏi bảng phân loại.` })
      }
      await client.invalidateQueries({ queryKey: ['admin', 'webfilter', 'catalog'] })
    },
    onError: (error) => showToast({ tone: 'error', message: saveErrorMessage(error) }),
  })

  const filteredEntries = useMemo(() => {
    const term = search.trim().toLowerCase()
    return (catalog.data ?? []).filter((entry) => entry.domain.includes(term))
  }, [catalog.data, search])
  const totalPages = Math.max(1, Math.ceil(filteredEntries.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const pageEntries = filteredEntries.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)
  const unclassifiedCount = catalog.data?.filter((entry) => entry.category === 'unclassified').length ?? 0
  const categoryCount = new Set(catalog.data?.map((entry) => entry.category) ?? []).size

  function addDomain(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const parsed = catalogFormSchema.safeParse({ domain, category })
    if (!parsed.success) {
      showToast({ tone: 'error', message: parsed.error.issues[0].message })
      return
    }
    save.mutate({ ...parsed.data, action: 'add' })
  }

  function openEdit(entry: CatalogEntry) {
    setEditing(entry)
    setEditCategory(entry.category)
  }

  if (catalog.isPending) {
    return (
      <div className="grid place-items-center py-20">
        <Spinner size="lg" />
      </div>
    )
  }
  if (catalog.isError) return <Alert tone="error">Không tải được bảng phân loại.</Alert>

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Bảng phân loại website</h1>
        <p className="mt-1 text-ink-muted">Quản lý danh mục tên miền dùng chung cho mọi hồ sơ gia đình.</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Metric
          label="Tên miền trong danh mục"
          value={catalog.data.length}
          icon={Globe2}
          tone="bg-sky-100/80 text-sky-700"
        />
        <Metric label="Nhóm đang sử dụng" value={categoryCount} icon={Tags} tone="bg-violet-100/80 text-violet-700" />
        <Metric
          label="Chưa phân loại"
          value={unclassifiedCount}
          icon={CircleHelp}
          tone="bg-amber-100/80 text-amber-700"
        />
      </div>

      <Card strong title="Thêm tên miền" description="Tên miền mới sẽ được thêm vào danh mục dùng chung.">
        <form className="flex flex-col gap-4" onSubmit={addDomain} noValidate>
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField
              label="Tên miền"
              value={domain}
              onChange={(event) => setDomain(event.target.value)}
              placeholder="example.com"
              autoComplete="off"
            />
            <Select
              label="Nhóm phân loại"
              options={WEB_CATEGORIES.map((item) => ({ value: item, label: CATEGORY_LABELS[item] }))}
              value={category}
              onChange={(event) => setCategory(event.target.value as WebCategory)}
            />
          </div>
          <div className="flex justify-end">
            <Button type="submit" loading={save.isPending} disabled={save.isPending}>
              <Plus aria-hidden="true" className="size-4" />
              Thêm vào danh mục
            </Button>
          </div>
        </form>
      </Card>

      <Card
        strong
        title="Danh sách tên miền"
        description="Đổi nhóm trực tiếp qua thao tác sửa. Xóa sẽ gỡ tên miền khỏi danh mục dùng chung."
      >
        <div className="mb-4 max-w-sm">
          <TextField
            label="Tìm tên miền"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
              setPage(1)
            }}
            placeholder="Nhập tên miền để lọc…"
          />
        </div>
        {filteredEntries.length === 0 ? (
          <EmptyState
            compact
            icon={Globe2}
            message={search ? 'Không tìm thấy tên miền phù hợp.' : 'Danh mục chưa có tên miền nào.'}
          />
        ) : (
          <Table>
            <TableHead>
              <TableRow>
                <Th>Tên miền</Th>
                <Th>Nhóm phân loại</Th>
                <Th>Cập nhật lần cuối</Th>
                <Th>
                  <span className="sr-only">Thao tác</span>
                </Th>
              </TableRow>
            </TableHead>
            <TableBody>
              {pageEntries.map((entry) => (
                <TableRow key={entry.domain}>
                  <Td className="font-mono text-sm font-medium text-ink">{entry.domain}</Td>
                  <Td>
                    <Badge tone={CATEGORY_TONES[entry.category]}>{CATEGORY_LABELS[entry.category]}</Badge>
                  </Td>
                  <Td className="whitespace-nowrap text-sm text-ink-muted">{formatDateTime(entry.updated_at)}</Td>
                  <Td className="text-right">
                    <div className="inline-flex items-center gap-1">
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={save.isPending}
                        aria-label={`Sửa phân loại ${entry.domain}`}
                        onClick={() => openEdit(entry)}
                      >
                        <Pencil aria-hidden="true" className="size-4" />
                        Sửa
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={save.isPending}
                        aria-label={`Xóa ${entry.domain}`}
                        onClick={() => setRemovingDomain(entry.domain)}
                      >
                        <Trash2 aria-hidden="true" className="size-4 text-rose-600" />
                      </Button>
                    </div>
                  </Td>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        {filteredEntries.length > 0 && totalPages > 1 && (
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-ink-muted">
              {Math.min((currentPage - 1) * PAGE_SIZE + 1, filteredEntries.length)}–
              {Math.min(currentPage * PAGE_SIZE, filteredEntries.length)} trong {filteredEntries.length} tên miền
            </p>
            <Pagination
              page={currentPage}
              totalPages={totalPages}
              onPageChange={setPage}
              disabled={save.isPending}
              ariaLabel="Phân trang danh mục tên miền"
            />
          </div>
        )}
      </Card>

      <Dialog
        open={editing !== null}
        title="Sửa phân loại tên miền"
        onClose={() => !save.isPending && setEditing(null)}
        actions={
          <>
            <Button variant="ghost" disabled={save.isPending} onClick={() => setEditing(null)}>
              Hủy
            </Button>
            <Button
              loading={save.isPending && save.variables?.action === 'update'}
              disabled={save.isPending || editing === null}
              onClick={() =>
                editing && save.mutate({ domain: editing.domain, category: editCategory, action: 'update' })
              }
            >
              Lưu thay đổi
            </Button>
          </>
        }
      >
        {editing && (
          <div className="flex flex-col gap-4">
            <p className="font-mono text-ink">{editing.domain}</p>
            <Select
              label="Nhóm phân loại"
              options={WEB_CATEGORIES.map((item) => ({ value: item, label: CATEGORY_LABELS[item] }))}
              value={editCategory}
              onChange={(event) => setEditCategory(event.target.value as WebCategory)}
            />
          </div>
        )}
      </Dialog>

      <Dialog
        open={removingDomain !== null}
        title="Xóa tên miền khỏi danh mục?"
        onClose={() => !save.isPending && setRemovingDomain(null)}
        actions={
          <>
            <Button variant="ghost" disabled={save.isPending} onClick={() => setRemovingDomain(null)}>
              Hủy
            </Button>
            <Button
              variant="danger"
              loading={save.isPending && save.variables?.action === 'delete'}
              disabled={save.isPending || removingDomain === null}
              onClick={() =>
                removingDomain && save.mutate({ domain: removingDomain, category: null, action: 'delete' })
              }
            >
              <Trash2 aria-hidden="true" className="size-4" />
              Xóa tên miền
            </Button>
          </>
        }
      >
        <p>
          Tên miền <strong className="font-mono text-ink">{removingDomain}</strong> sẽ bị xóa khỏi danh mục dùng chung.
        </p>
        <p className="mt-2">Thay đổi sẽ tạo phiên bản chính sách mới cho các hồ sơ gia đình.</p>
        <p className="mt-2">Danh mục cần giữ tối thiểu 200 tên miền.</p>
      </Dialog>
    </div>
  )
}
