/*
 * Quotas and the schedule save separately with a partial PATCH, so saving one never overwrites unsaved edits of
 * the other. Each form is keyed by policy_version so it resets to the server value after every save.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '@/shared/api/client.ts'
import {
  getPolicy,
  getPolicyChild,
  policyChildKey,
  policyKey,
  policyVersionsKey,
  updatePolicy,
} from '@/shared/api/policy.ts'
import { Alert, Card, Spinner } from '@/shared/components/index.ts'
import type { Policy, PolicyUpdate } from '@/shared/types/policy.ts'
import QuotaForm from '@/features/screentime/components/QuotaForm.tsx'
import ScheduleGrid from '@/features/screentime/components/ScheduleGrid.tsx'
import AppGroupForm from '@/features/screentime/components/AppGroupForm.tsx'
import { screentimeErrorMessage } from '@/features/screentime/utils/messages.ts'

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

export default function ScreenTimePage() {
  const id = parseId(useParams().id)
  if (id === null) return <NotFound />
  return <ScreenTime id={id} />
}

function usePolicyMutation(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: PolicyUpdate) => updatePolicy(id, body),
    onSuccess: (data: Policy) => {
      queryClient.setQueryData(policyKey(id), data)
      queryClient.invalidateQueries({ queryKey: policyVersionsKey(id) })
    },
  })
}

function ScreenTime({ id }: { id: number }) {
  const child = useQuery({ queryKey: policyChildKey(id), queryFn: () => getPolicyChild(id) })
  const policy = useQuery({ queryKey: policyKey(id), queryFn: () => getPolicy(id) })
  const quotas = usePolicyMutation(id)
  const schedule = usePolicyMutation(id)
  const groups = usePolicyMutation(id)
  const [savedQuotas, setSavedQuotas] = useState(false)
  const [savedSchedule, setSavedSchedule] = useState(false)
  const [savedGroups, setSavedGroups] = useState(false)

  if (child.isPending || policy.isPending) {
    return (
      <div className="grid place-items-center py-20">
        <Spinner size="lg" />
      </div>
    )
  }
  if (policy.error instanceof ApiError && policy.error.status === 404) return <NotFound />
  if (policy.isError) return <Alert tone="error">{screentimeErrorMessage(policy.error)}</Alert>

  const data = policy.data
  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="text-sm">
          <Link to={`/children/${id}`}>← {child.data?.name ?? 'Thông tin của con'}</Link>
        </p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-ink sm:text-3xl">Thời gian dùng máy</h1>
        <p className="mt-1 text-ink-muted">
          Trẻ chỉ dùng được khi vừa còn thời gian trong giới hạn ngày, vừa đang trong khung giờ cho phép. Điều kiện nào
          đến trước thì máy khóa. Ví dụ: lịch cả ngày và giới hạn 2 giờ vẫn chỉ cho dùng tối đa 2 giờ. Tray báo trước
          10, 5 và 1 phút. Đang áp phiên bản {data.policy_version}.{' '}
          <Link to={`/children/${id}/policy`}>Xem chính sách</Link>
        </p>
      </div>

      <Card
        title="Giới hạn tổng thời gian mỗi ngày"
        description="Hạn mức riêng cho ngày thường và cuối tuần; không tính khi máy khóa hoặc trẻ không thao tác quá 5 phút."
      >
        <QuotaForm
          key={`quota-${data.policy_version}`}
          initial={data}
          pending={quotas.isPending}
          error={quotas.error}
          saved={savedQuotas}
          onSubmit={(body) => {
            setSavedQuotas(false)
            quotas.mutate(body, { onSuccess: () => setSavedQuotas(true) })
          }}
        />
      </Card>

      <Card
        title="Lịch trong tuần"
        description="Ô xanh là giờ được dùng theo giờ máy của con. Giờ xanh không làm tăng hạn mức ngày."
      >
        <ScheduleGrid
          key={`schedule-${data.policy_version}`}
          initial={data.weekly_schedule}
          pending={schedule.isPending}
          error={schedule.error}
          saved={savedSchedule}
          onSubmit={(days) => {
            setSavedSchedule(false)
            schedule.mutate({ weekly_schedule: days }, { onSuccess: () => setSavedSchedule(true) })
          }}
        />
      </Card>

      <Card
        title="Ngân sách theo nhóm ứng dụng"
        description="Mỗi nhóm có bộ đếm riêng, đặt lại vào đầu ngày. Để trống để không giới hạn."
      >
        {groups.error != null && <Alert tone="error">{screentimeErrorMessage(groups.error)}</Alert>}
        {savedGroups && groups.error == null && <Alert tone="success">Đã lưu nhóm và ngân sách ứng dụng.</Alert>}
        <AppGroupForm
          key={`groups-${data.policy_version}`}
          groups={data.app_groups}
          rules={data.app_rules}
          pending={groups.isPending}
          onSave={(app_groups) => {
            setSavedGroups(false)
            groups.mutate({ app_groups }, { onSuccess: () => setSavedGroups(true) })
          }}
        />
      </Card>
    </div>
  )
}
