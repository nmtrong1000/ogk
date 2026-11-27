import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ChartLine } from 'lucide-react'
import { ApiError } from '@/shared/api/client.ts'
import { commonErrorMessage } from '@/shared/api/errors.ts'
import { getPolicyChild, policyChildKey } from '@/shared/api/policy.ts'
import { Alert, Card, ChildPageHeader, Select, Spinner } from '@/shared/components/index.ts'
import { formatDuration } from '@/shared/utils/duration.ts'
import { getReport, reportKey } from '@/features/reports/api.ts'
import BlockedStats from '@/features/reports/components/BlockedStats.tsx'
import RequestsList from '@/features/reports/components/RequestsList.tsx'
import TopList from '@/features/reports/components/TopList.tsx'
import UsageChart from '@/features/reports/components/UsageChart.tsx'

const RANGES = [
  { value: '7', label: '7 ngày gần nhất' },
  { value: '30', label: '30 ngày gần nhất' },
  { value: '90', label: '90 ngày gần nhất' },
]

function parseId(value: string | undefined): number | null {
  return value && /^\d+$/.test(value) ? Number(value) : null
}

function NotFound() {
  return (
    <Card strong className="mx-auto max-w-md text-center">
      <h1 className="text-xl font-bold text-ink">Không tìm thấy</h1>
      <p className="mt-2 text-ink-muted">Không có thông tin của con này, hoặc bạn không có quyền xem.</p>
      <p className="mt-5">
        <Link to="/children">Về danh sách các con</Link>
      </p>
    </Card>
  )
}

export default function ReportsPage() {
  const id = parseId(useParams().id)
  if (id === null) return <NotFound />
  return <Reports id={id} />
}

function Reports({ id }: { id: number }) {
  const [days, setDays] = useState(7)
  const child = useQuery({ queryKey: policyChildKey(id), queryFn: () => getPolicyChild(id) })
  const report = useQuery({
    queryKey: reportKey(id, days),
    queryFn: () => getReport(id, days),
    placeholderData: (previous) => previous,
  })

  if (child.error instanceof ApiError && child.error.status === 404) return <NotFound />
  const data = report.data
  const maxApp = Math.max(1, ...(data?.top_apps.map((a) => a.seconds) ?? []))
  const maxDomain = Math.max(1, ...(data?.top_domains.map((d) => d.count) ?? []))

  return (
    <div className="flex flex-col gap-6">
      <ChildPageHeader
        title="Báo cáo sử dụng"
        description={`Thời gian dùng máy, ứng dụng và website ${child.data ? `của ${child.data.name}` : ''}. Con xem được cùng số liệu này từ biểu tượng OGK trên máy.`}
        icon={ChartLine}
      />

      <Select
        label="Khoảng thời gian"
        options={RANGES}
        value={String(days)}
        onChange={(event) => setDays(Number(event.target.value))}
        className="sm:max-w-xs"
      />

      {report.isError && <Alert tone="error">{commonErrorMessage(report.error)}</Alert>}
      {report.isPending && (
        <div className="grid place-items-center py-12">
          <Spinner size="lg" />
        </div>
      )}

      {data && (
        <>
          <Card
            title="Thời gian dùng máy"
            description={`Tổng ${formatDuration(data.total_seconds)} · giới hạn hôm nay ${formatDuration(data.quota_today_seconds)}`}
          >
            <UsageChart daily={data.daily} weekly={data.weekly} />
          </Card>

          <Card title="Số lần bị chặn">
            <BlockedStats blocked={data.blocked} />
          </Card>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <Card title="Top 10 ứng dụng" description="Theo thời gian ở cửa sổ đang dùng">
              <TopList
                empty="Chưa có dữ liệu ứng dụng."
                items={data.top_apps.map((a) => ({
                  key: a.name,
                  label: a.name,
                  value: formatDuration(a.seconds),
                  ratio: a.seconds / maxApp,
                }))}
              />
            </Card>
            <Card title="Top 10 website" description="Theo số lần truy cập">
              <TopList
                empty="Chưa có dữ liệu website."
                items={data.top_domains.map((d) => ({
                  key: d.domain,
                  label: d.domain,
                  value: `${d.count} lần`,
                  ratio: d.count / maxDomain,
                }))}
              />
            </Card>
          </div>
        </>
      )}

      <Card title="Yêu cầu của con">
        <RequestsList childId={id} />
      </Card>

      {data && <p className="text-xs text-ink-muted">Ngày tính theo múi giờ {data.time_zone}.</p>}
    </div>
  )
}
