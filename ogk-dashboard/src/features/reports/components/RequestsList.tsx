import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Alert, Badge, Button, Spinner } from '@/shared/components/index.ts'
import type { ReportRequest } from '@/shared/types/reports.ts'
import { getReportRequests, reportRequestsKey } from '@/features/reports/api.ts'

const PAGE_SIZE = 10

function status(item: ReportRequest) {
  if (item.status === 'pending') return <Badge tone="warning">Đang chờ</Badge>
  if (item.status === 'approved') return <Badge tone="success">Đã duyệt</Badge>
  return <Badge tone="danger">Đã từ chối</Badge>
}

export default function RequestsList({ childId }: { childId: number }) {
  const [page, setPage] = useState(1)
  const query = useQuery({
    queryKey: reportRequestsKey(childId, page),
    queryFn: () => getReportRequests(childId, page, PAGE_SIZE),
    placeholderData: (previous) => previous,
  })
  if (query.isPending) return <Spinner />
  if (query.isError) return <Alert tone="error">Không tải được danh sách yêu cầu.</Alert>
  const { items, total } = query.data
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  if (total === 0) return <p className="py-4 text-sm text-ink-muted">Con chưa gửi yêu cầu nào.</p>
  return (
    <div className="flex flex-col gap-4">
      <ul className="flex flex-col divide-y divide-brand-100">
        {items.map((item) => (
          <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
            <div className="min-w-0">
              <p className="truncate text-sm text-ink">
                {item.type === 'add_time' ? 'Xin thêm giờ' : `Báo chặn nhầm: ${item.domain}`}
              </p>
              <p className="text-xs text-ink-muted">{new Date(item.created_at).toLocaleString('vi-VN')}</p>
            </div>
            {status(item)}
          </li>
        ))}
      </ul>
      {pages > 1 && (
        <div className="flex items-center justify-between gap-2 text-sm text-ink-muted">
          <Button size="sm" variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Trước
          </Button>
          <span>
            Trang {page}/{pages}
          </span>
          <Button size="sm" variant="secondary" disabled={page >= pages} onClick={() => setPage(page + 1)}>
            Sau
          </Button>
        </div>
      )}
    </div>
  )
}
