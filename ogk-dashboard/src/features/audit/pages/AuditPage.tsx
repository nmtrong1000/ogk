import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { commonErrorMessage } from '@/shared/api/errors.ts'
import {
  Alert,
  Badge,
  Card,
  EmptyState,
  Pagination,
  Spinner,
  Table,
  TableBody,
  TableHead,
  TableRow,
  Td,
  Th,
} from '@/shared/components/index.ts'
import type { AuditEntry } from '@/shared/types/audit.ts'
import { formatDateTime } from '@/shared/utils/dateTime.ts'
import { auditKey, listAudit, PAGE_SIZE } from '@/features/audit/api.ts'
import ChangeSummary from '@/features/audit/components/ChangeSummary.tsx'
import { ACTION_TONES, actionLabel } from '@/features/audit/utils/format.ts'

function ActionBadge({ entry }: { entry: AuditEntry }) {
  return <Badge tone={ACTION_TONES[entry.action] ?? 'neutral'}>{actionLabel(entry)}</Badge>
}

function Actor({ entry }: { entry: AuditEntry }) {
  return <span className="break-all">{entry.actor_email ?? `Tài khoản #${entry.actor_id}`}</span>
}

export default function AuditPage() {
  const [page, setPage] = useState(1)
  const audit = useQuery({
    queryKey: auditKey(page),
    queryFn: () => listAudit(page),
    placeholderData: keepPreviousData,
  })
  const data = audit.data
  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Nhật ký thay đổi</h1>
        <p className="mt-1 text-ink-muted">Ai đã thay đổi gì, lúc nào và từ địa chỉ IP nào.</p>
      </div>

      <Card
        title="Các thay đổi"
        description={data ? `${data.total} thay đổi` : undefined}
        actions={audit.isFetching && !audit.isPending ? <Spinner size="sm" label="Đang tải" /> : undefined}
      >
        <div className="flex flex-col gap-4">
          {audit.isPending && (
            <div className="grid place-items-center py-8">
              <Spinner />
            </div>
          )}
          {audit.isError && <Alert tone="error">{commonErrorMessage(audit.error)}</Alert>}
          {data?.items.length === 0 && <EmptyState message="Chưa có thay đổi nào." />}

          {data && data.items.length > 0 && (
            <Table className="min-w-[900px]">
              <TableHead>
                <tr>
                  <Th>Thời điểm</Th>
                  <Th>Thao tác</Th>
                  <Th>Thay đổi</Th>
                  <Th>Người thực hiện</Th>
                  <Th>IP</Th>
                </tr>
              </TableHead>
              <TableBody>
                {data.items.map((entry) => (
                  <TableRow key={entry.id}>
                    <Td className="whitespace-nowrap">
                      <time dateTime={entry.at}>{formatDateTime(entry.at)}</time>
                    </Td>
                    <Td>
                      <ActionBadge entry={entry} />
                    </Td>
                    <Td>
                      <ChangeSummary entry={entry} />
                    </Td>
                    <Td>
                      <Actor entry={entry} />
                    </Td>
                    <Td className="whitespace-nowrap font-mono text-xs">{entry.ip}</Td>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {data && data.total > PAGE_SIZE && (
            <Pagination page={page} totalPages={pages} onPageChange={setPage} disabled={audit.isPlaceholderData} />
          )}
        </div>
      </Card>
    </div>
  )
}
