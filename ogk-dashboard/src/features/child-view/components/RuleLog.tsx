import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, Pagination, Spinner } from '@/shared/components/index.ts'
import { formatDateTime } from '@/shared/utils/dateTime.ts'
import { childViewRuleLogKey, getChildViewRuleLog } from '@/features/child-view/api.ts'
import { describeChanges } from '@/features/child-view/utils/describe.ts'
import { childViewErrorMessage } from '@/features/child-view/utils/messages.ts'
import ChildNotice from '@/features/child-view/components/ChildNotice.tsx'

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
      {query.isError && (
        <ChildNotice compact title="Chưa tải được nhật ký" message={childViewErrorMessage(query.error)} />
      )}
      {query.data && query.data.total === 0 && (
        <p className="text-base text-ink-muted">Bố mẹ chưa thay đổi luật nào.</p>
      )}
      {query.data && query.data.total > 0 && (
        <div className="flex flex-col gap-4">
          <ol className="flex flex-col gap-4">
            {query.data.items.map((entry) => (
              <li key={entry.id} className="border-l-4 border-brand-300 pl-3">
                <p className="text-sm text-ink-muted">{formatDateTime(entry.at)}</p>
                <ul className="mt-1 flex flex-col gap-1 text-base text-ink">
                  {describeChanges(entry.changes).map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
          <Pagination
            page={page}
            totalPages={Math.ceil(query.data.total / PAGE_SIZE)}
            onPageChange={setPage}
            disabled={query.isFetching}
            previousLabel="Mới hơn"
            nextLabel="Cũ hơn"
          />
        </div>
      )}
    </Card>
  )
}
