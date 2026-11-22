import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Alert, Button, Card, Spinner, TextField } from '@/shared/components/index.ts'
import { getCatalog, updateCatalog, WEB_CATEGORIES, type WebCategory } from '@/features/webfilter/api.ts'

const labels: Record<WebCategory, string> = {
  education: 'Giáo dục',
  entertainment: 'Giải trí',
  social: 'Mạng xã hội',
  games: 'Trò chơi',
  adult: 'Không phù hợp lứa tuổi',
  unclassified: 'Chưa phân loại',
}

export default function AdminCatalogPage() {
  const client = useQueryClient()
  const catalog = useQuery({ queryKey: ['admin', 'webfilter', 'catalog'], queryFn: getCatalog })
  const [domain, setDomain] = useState('')
  const [category, setCategory] = useState<WebCategory>('unclassified')
  const save = useMutation({
    mutationFn: ({ name, group }: { name: string; group: WebCategory | null }) => updateCatalog(name, group),
    onSuccess: () => client.invalidateQueries({ queryKey: ['admin', 'webfilter', 'catalog'] }),
  })
  if (catalog.isPending)
    return (
      <div className="grid place-items-center py-20">
        <Spinner size="lg" />
      </div>
    )
  if (catalog.isError) return <Alert tone="error">Không tải được bảng phân loại.</Alert>
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">Bảng phân loại website</h1>
        <p className="mt-1 text-ink-muted">Cập nhật phân loại dùng chung. {catalog.data.length} tên miền hiện có.</p>
      </div>
      {save.error && <Alert tone="error">Không lưu được thay đổi.</Alert>}
      <Card title="Thêm hoặc đổi phân loại">
        <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
          <TextField
            label="Tên miền"
            value={domain}
            onChange={(event) => setDomain(event.target.value)}
            placeholder="example.com"
          />
          <label className="flex flex-col gap-1.5 text-sm font-medium">
            Nhóm
            <select
              className="glass-input h-11 rounded-control px-3"
              value={category}
              onChange={(event) => setCategory(event.target.value as WebCategory)}
            >
              {WEB_CATEGORIES.map((item) => (
                <option key={item} value={item}>
                  {labels[item]}
                </option>
              ))}
            </select>
          </label>
          <Button
            className="self-end"
            disabled={!domain.trim() || save.isPending}
            onClick={() => {
              save.mutate({ name: domain.trim(), group: category })
              setDomain('')
            }}
          >
            Lưu phân loại
          </Button>
        </div>
      </Card>
      <Card title="Danh sách" description="Chọn nhóm để sửa trực tiếp. Xóa bỏ tên miền khỏi bảng phân loại.">
        <div className="max-h-[65vh] overflow-auto">
          {catalog.data.map((entry) => (
            <div
              key={entry.domain}
              className="grid grid-cols-[1fr_1fr_auto] items-center gap-3 border-b border-line/60 py-2"
            >
              <span>{entry.domain}</span>
              <select
                className="glass-input h-9 rounded-control px-2 text-sm"
                value={entry.category}
                disabled={save.isPending}
                onChange={(event) => save.mutate({ name: entry.domain, group: event.target.value as WebCategory })}
              >
                {WEB_CATEGORIES.map((item) => (
                  <option key={item} value={item}>
                    {labels[item]}
                  </option>
                ))}
              </select>
              <Button
                size="sm"
                variant="ghost"
                disabled={save.isPending}
                onClick={() => save.mutate({ name: entry.domain, group: null })}
              >
                Xóa
              </Button>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
