import { useMutation, useQuery } from '@tanstack/react-query'
import { Button, Card, Spinner } from '@/shared/components/index.ts'
import {
  childViewMeKey,
  childViewTodayKey,
  closeChildView,
  getChildViewMe,
  getChildViewToday,
} from '@/features/child-view/api.ts'
import RuleLog from '@/features/child-view/components/RuleLog.tsx'
import TodaySummary from '@/features/child-view/components/TodaySummary.tsx'
import ChildNotice from '@/features/child-view/components/ChildNotice.tsx'
import { childViewErrorMessage } from '@/features/child-view/utils/messages.ts'

export default function ChildViewPage() {
  const me = useQuery({ queryKey: childViewMeKey, queryFn: getChildViewMe })
  const today = useQuery({ queryKey: childViewTodayKey, queryFn: getChildViewToday, enabled: me.isSuccess })
  const close = useMutation({ mutationFn: closeChildView })

  if (close.isSuccess) {
    return (
      <Card strong className="mx-auto max-w-md text-center">
        <p className="py-4 text-lg text-ink">Đã đóng báo cáo. Em có thể tắt trang này.</p>
      </Card>
    )
  }
  if (me.isPending) {
    return (
      <div className="grid place-items-center py-20">
        <Spinner size="lg" />
      </div>
    )
  }
  if (me.isError) {
    return (
      <div className="grid min-h-[min(62dvh,38rem)] place-items-center py-8">
        <ChildNotice title="Không thể mở báo cáo" message={childViewErrorMessage(me.error)} />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Chào {me.data.name}!</h1>
          <p className="mt-1 text-lg text-ink-muted">Đây là những gì em đã dùng hôm nay.</p>
        </div>
        <Button variant="secondary" loading={close.isPending} onClick={() => close.mutate()}>
          Đóng báo cáo
        </Button>
      </div>
      {today.isError && (
        <ChildNotice compact title="Chưa tải được báo cáo hôm nay" message={childViewErrorMessage(today.error)} />
      )}
      {today.isPending && (
        <div className="grid place-items-center py-12">
          <Spinner size="lg" />
        </div>
      )}
      {today.data && <TodaySummary report={today.data} />}
      <RuleLog />
    </div>
  )
}
