import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Card, Spinner } from '@/shared/components/index.ts'
import { childViewRuleLogKey, getChildViewRuleLog } from '@/features/child-view/api.ts'
import { describeChanges } from '@/features/child-view/utils/describe.ts'
import { childViewErrorMessage } from '@/features/child-view/utils/messages.ts'

const PAGE_SIZE = 10

export default function RuleLog() {
  const [page, setPage] = useState(1)
  const query = useQuery({
    queryKey: childViewRuleLogKey(page),
    queryFn: () => getChildViewRuleLog(page, PAGE_SIZE),
    placeholderData: (previous) => previous,
  })
  return (
    <Card title="Bố mẹ đã thay đổi gì" description="Những lần bố mẹ đổi luật dùng máy của em.">
      {query.isPending && <Spinner />}
      {query.isError && <Alert tone="error">{childViewErrorMessage(query.error)}</Alert>}
      {query.data && query.data.total === 0 && (
        <p className="text-base text-ink-muted">Bố mẹ chưa thay đổi luật nào.</p>
      )}
      {query.data && query.data.total > 0 && (
        <div className="flex flex-col gap-4">
          <ol className="flex flex-col gap-4">
            {query.data.items.map((entry) => (
              <li key={entry.id} className="border-l-4 border-brand-300 pl-3">
                <p className="text-sm text-ink-muted">{new Date(entry.at).toLocaleString('vi-VN')}</p>
                <ul className="mt-1 flex flex-col gap-1 text-base text-ink">
                  {describeChanges(entry.changes).map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
          {query.data.total > PAGE_SIZE && (
            <div className="flex items-center justify-between gap-2 text-sm text-ink-muted">
              <Button size="sm" variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                Mới hơn
              </Button>
              <span>
                Trang {page}/{Math.ceil(query.data.total / PAGE_SIZE)}
              </span>
              <Button
                size="sm"
                variant="secondary"
                disabled={page * PAGE_SIZE >= query.data.total}
                onClick={() => setPage(page + 1)}
              >
                Cũ hơn
              </Button>
            </div>
          )}
        </div>
      )}
    </Card>
  )
}
