import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/shared/api/client.ts'
import { Badge, Card, Spinner } from '@/shared/components/index.ts'
import type { Health } from '@/shared/types/health.ts'

export default function HomePage() {
  const { data, error, isPending } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiFetch<Health>('/api/health'),
  })

  let status = <Spinner size="sm" label="Đang kiểm tra" />
  if (error) status = <Badge tone="danger">Lỗi: {error.message}</Badge>
  else if (!isPending) status = <Badge tone={data.status === 'ok' ? 'success' : 'warning'}>{data.status}</Badge>

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Tổng quan</h1>
        <p className="mt-1 text-ink-muted">Quản lý việc sử dụng máy tính của con.</p>
      </div>
      <Card title="Trạng thái server">
        <div className="flex items-center gap-3 text-sm text-ink-muted">Kết nối tới OGK-Server: {status}</div>
      </Card>
    </div>
  )
}
