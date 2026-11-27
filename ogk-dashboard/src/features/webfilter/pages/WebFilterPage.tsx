import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Globe } from 'lucide-react'
import { ApiError } from '@/shared/api/client.ts'
import {
  getPolicyChild,
  policyChildKey,
  policyKey,
  policyVersionsKey,
  getPolicy,
  updatePolicy,
} from '@/shared/api/policy.ts'
import { Alert, Button, Card, ChildPageHeader, Spinner, TextField } from '@/shared/components/index.ts'
import type { Policy } from '@/shared/types/policy.ts'
import { WEB_CATEGORIES } from '@/features/webfilter/api.ts'

const names: Record<string, string> = {
  education: 'Giáo dục',
  entertainment: 'Giải trí',
  social: 'Mạng xã hội',
  games: 'Trò chơi',
  adult: 'Không phù hợp lứa tuổi',
  unclassified: 'Chưa phân loại',
}

export default function WebFilterPage() {
  const id = Number(useParams().id)
  const client = useQueryClient()
  const child = useQuery({ queryKey: policyChildKey(id), queryFn: () => getPolicyChild(id) })
  const policy = useQuery({ queryKey: policyKey(id), queryFn: () => getPolicy(id) })
  const [domain, setDomain] = useState('')
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
  const toggle = (key: 'web_allowlist' | 'web_blocklist', value: string) => {
    const items = current[key]
    save.mutate({ [key]: items.includes(value) ? items.filter((x) => x !== value) : [...items, value] })
  }
  return (
    <div className="flex flex-col gap-6">
      <ChildPageHeader
        title="Lọc website"
        description="Luật miễn chặn luôn được ưu tiên hơn luật chặn."
        icon={Globe}
      />
      {save.error && <Alert tone="error">Không lưu được luật website.</Alert>}
      <Card title="Nhóm bị chặn" description="Chọn nhóm áp dụng cho tài khoản trẻ này.">
        <div className="grid gap-3 sm:grid-cols-2">
          {WEB_CATEGORIES.map((category) => (
            <label key={category} className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={current.blocked_categories.includes(category)}
                disabled={save.isPending}
                onChange={() =>
                  save.mutate({
                    blocked_categories: current.blocked_categories.includes(category)
                      ? current.blocked_categories.filter((x) => x !== category)
                      : [...current.blocked_categories, category],
                  })
                }
              />
              {names[category]}
            </label>
          ))}
        </div>
      </Card>
      <Card
        title="Tên miền riêng"
        description="Tên miền và tên miền con cùng chịu luật. Ví dụ example.com áp dụng cả a.example.com."
      >
        <div className="flex flex-col gap-3 sm:flex-row">
          <TextField
            label="Tên miền"
            value={domain}
            onChange={(event) => setDomain(event.target.value)}
            placeholder="example.com"
          />
          <div className="flex gap-2 sm:items-end">
            <Button
              disabled={save.isPending || !domain.trim()}
              onClick={() => {
                const value = domain.trim().toLowerCase()
                save.mutate({ web_blocklist: [...new Set([...current.web_blocklist, value])] })
                setDomain('')
              }}
            >
              Chặn tên miền
            </Button>
            <Button
              variant="secondary"
              disabled={save.isPending || !domain.trim()}
              onClick={() => {
                const value = domain.trim().toLowerCase()
                save.mutate({ web_allowlist: [...new Set([...current.web_allowlist, value])] })
                setDomain('')
              }}
            >
              Miễn chặn
            </Button>
          </div>
        </div>
        <div className="mt-5 grid gap-5 sm:grid-cols-2">
          <div>
            <h3 className="font-semibold">Danh sách chặn</h3>
            {current.web_blocklist.map((item) => (
              <p key={item} className="flex justify-between py-1">
                {item}
                <button onClick={() => toggle('web_blocklist', item)}>Xóa</button>
              </p>
            ))}
          </div>
          <div>
            <h3 className="font-semibold">Danh sách miễn chặn</h3>
            {current.web_allowlist.map((item) => (
              <p key={item} className="flex justify-between py-1">
                {item}
                <button onClick={() => toggle('web_allowlist', item)}>Xóa</button>
              </p>
            ))}
          </div>
        </div>
      </Card>
    </div>
  )
}
