import { AppWindow, Globe } from 'lucide-react'
import { Card, EmptyState } from '@/shared/components/index.ts'
import type { Report } from '@/shared/types/reports.ts'
import { formatDuration } from '@/shared/utils/duration.ts'
import Illustration from '@/features/child-view/components/Illustration.tsx'

function moodFor(used: number, quota: number) {
  if (quota > 0 && used >= quota) return 'rest' as const
  if (quota > 0 && used >= quota * 0.8) return 'calm' as const
  return 'happy' as const
}

function encouragement(used: number, quota: number) {
  if (quota === 0) return 'Hôm nay là ngày nghỉ máy. Cùng chơi ngoài trời nhé!'
  if (used >= quota) return 'Em đã dùng hết giờ hôm nay. Nghỉ ngơi cho mắt khỏe nhé!'
  return `Em còn khoảng ${formatDuration(quota - used)} để dùng máy hôm nay.`
}

export default function TodaySummary({ report }: { report: Report }) {
  const used = report.daily.at(-1)?.seconds ?? 0
  const quota = report.quota_today_seconds
  const percent = quota > 0 ? Math.min(100, Math.round((used / quota) * 100)) : 100
  const topApps = report.top_apps.slice(0, 3)
  const topSites = report.top_domains.slice(0, 3)

  return (
    <div className="flex flex-col gap-6">
      <Card strong className="text-center">
        <div className="flex flex-col items-center gap-4">
          <Illustration mood={moodFor(used, quota)} />
          <p className="text-2xl font-bold text-ink sm:text-3xl">Hôm nay em đã dùng máy {formatDuration(used)}</p>
          <div className="w-full max-w-md">
            <div
              className="h-4 overflow-hidden rounded-full bg-brand-100"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={percent}
              aria-label="Phần thời gian đã dùng hôm nay"
            >
              <div
                className={percent >= 100 ? 'h-full rounded-full bg-amber-400' : 'h-full rounded-full bg-brand-500'}
                style={{ width: `${percent}%` }}
              />
            </div>
            <p className="mt-2 text-base text-ink-muted">Giới hạn hôm nay: {formatDuration(quota)}</p>
          </div>
          <p className="text-lg text-ink">{encouragement(used, quota)}</p>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Card title="Ứng dụng em dùng nhiều nhất">
          {topApps.length === 0 ? (
            <EmptyState message="Hôm nay em chưa dùng ứng dụng nào." icon={AppWindow} compact />
          ) : (
            <ul className="flex flex-col gap-2 text-base text-ink">
              {topApps.map((app) => (
                <li key={app.name} className="flex justify-between gap-3">
                  <span className="truncate">{app.name}</span>
                  <span className="shrink-0 font-semibold">{formatDuration(app.seconds)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Trang web em vào nhiều nhất">
          {topSites.length === 0 ? (
            <EmptyState message="Hôm nay em chưa vào trang web nào." icon={Globe} compact />
          ) : (
            <ul className="flex flex-col gap-2 text-base text-ink">
              {topSites.map((site) => (
                <li key={site.domain} className="flex justify-between gap-3">
                  <span className="truncate">{site.domain}</span>
                  <span className="shrink-0 font-semibold">{site.count} lần</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title="Số lần bị chặn hôm nay">
        <p className="text-base text-ink">
          {report.blocked.total === 0
            ? 'Hôm nay không có gì bị chặn. Giỏi lắm!'
            : `OGK đã chặn ${report.blocked.total} lần: ${report.blocked.apps} lần ứng dụng và ${report.blocked.domains} lần trang web.`}
        </p>
      </Card>
    </div>
  )
}
