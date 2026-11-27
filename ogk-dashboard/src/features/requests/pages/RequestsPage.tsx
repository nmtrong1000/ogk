import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarClock, Check, CircleCheck, CircleX, Clock3, Globe, Hourglass, MessageCircle, X } from 'lucide-react'
import { ApiError } from '@/shared/api/client.ts'
import { Alert, Badge, Button, Card, EmptyState, Spinner } from '@/shared/components/index.ts'
import { formatDateTime } from '@/shared/utils/dateTime.ts'
import { decideRequest, listRequests, requestsKey, type ChildRequest } from '@/features/requests/api.ts'

function statusBadge(status: ChildRequest['status']) {
  if (status === 'pending') {
    return (
      <Badge tone="warning">
        <Clock3 aria-hidden="true" className="size-3.5" />
        Đang chờ
      </Badge>
    )
  }
  if (status === 'approved') {
    return (
      <Badge tone="success">
        <CircleCheck aria-hidden="true" className="size-3.5" />
        Đã duyệt
      </Badge>
    )
  }
  return (
    <Badge tone="danger">
      <CircleX aria-hidden="true" className="size-3.5" />
      Đã từ chối
    </Badge>
  )
}

function errorText(error: unknown) {
  if (error instanceof ApiError && error.code === 'request_already_decided') return 'Yêu cầu này đã được xử lý.'
  return 'Chưa lưu được quyết định. Vui lòng thử lại.'
}

function Metric({
  label,
  value,
  icon: Icon,
  tone,
}: {
  label: string
  value: number
  icon: typeof Clock3
  tone: 'sky' | 'amber' | 'emerald'
}) {
  const tones = {
    sky: 'ring-sky-200/70 bg-sky-100/80 text-sky-700',
    amber: 'ring-amber-200/70 bg-amber-100/80 text-amber-700',
    emerald: 'ring-emerald-200/70 bg-emerald-100/80 text-emerald-700',
  }
  return (
    <div className="glass-strong flex min-w-0 items-center gap-3 rounded-glass p-4 ring-1 ring-inset ring-white/70">
      <span className={`grid size-11 shrink-0 place-items-center rounded-2xl ${tones[tone]}`}>
        <Icon aria-hidden="true" className="size-5" />
      </span>
      <div className="min-w-0">
        <p className="text-xs font-medium text-ink-muted">{label}</p>
        <p className="text-xl font-bold text-ink">{value}</p>
      </div>
    </div>
  )
}

export default function RequestsPage() {
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: requestsKey, queryFn: listRequests, refetchInterval: 10_000 })
  const [messages, setMessages] = useState<Record<number, string>>({})
  const mutation = useMutation({
    mutationFn: ({ id, approve }: { id: number; approve: boolean }) => decideRequest(id, approve, messages[id] ?? ''),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: requestsKey }),
  })
  const pendingCount = query.data?.filter((item) => item.status === 'pending').length ?? 0
  const completedCount = (query.data?.length ?? 0) - pendingCount

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Yêu cầu của con</h1>
        <p className="mt-1 text-ink-muted">Xem nội dung, gửi lời nhắn và phản hồi từng yêu cầu.</p>
      </div>

      {query.isError && <Alert tone="error">Không tải được danh sách yêu cầu.</Alert>}
      {mutation.isError && <Alert tone="error">{errorText(mutation.error)}</Alert>}
      {query.isPending && (
        <div className="grid place-items-center py-12">
          <Spinner />
        </div>
      )}
      {query.data?.length === 0 && (
        <Card strong>
          <EmptyState
            message="Chưa có yêu cầu nào."
            description="Khi con gửi yêu cầu từ máy tính, nội dung sẽ xuất hiện tại đây."
          />
        </Card>
      )}
      {query.data && query.data.length > 0 && (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <Metric label="Tổng yêu cầu" value={query.data.length} icon={MessageCircle} tone="sky" />
            <Metric label="Đang chờ xử lý" value={pendingCount} icon={Clock3} tone="amber" />
            <Metric label="Đã phản hồi" value={completedCount} icon={CircleCheck} tone="emerald" />
          </div>

          <div className="flex flex-col gap-4">
            {query.data.map((item) => {
              const isPending = item.status === 'pending'
              const isSubmitting = mutation.isPending && mutation.variables?.id === item.id
              const RequestIcon = item.type === 'add_time' ? Hourglass : Globe
              return (
                <Card key={item.id} strong className="min-w-0">
                  <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-3">
                      <span
                        className={`grid size-12 shrink-0 place-items-center rounded-2xl ${item.type === 'add_time' ? 'bg-sky-100/80 text-sky-700' : 'bg-violet-100/80 text-violet-700'}`}
                      >
                        <RequestIcon aria-hidden="true" className="size-5" />
                      </span>
                      <div className="min-w-0">
                        <h2 className="truncate text-lg font-semibold tracking-tight text-ink">{item.child_name}</h2>
                        <p className="mt-1 inline-flex items-center gap-2 text-sm text-ink-muted">
                          <CalendarClock aria-hidden="true" className="size-4 shrink-0" />
                          {formatDateTime(item.created_at)}
                        </p>
                      </div>
                    </div>
                    {statusBadge(item.status)}
                  </div>

                  <div className="mt-4 min-w-0 rounded-control bg-white/50 p-3.5 ring-1 ring-inset ring-white/70">
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-ink-muted">Nội dung yêu cầu</p>
                      <p className="mt-0.5 break-words font-semibold text-ink">
                        {item.type === 'add_time' ? (
                          'Xin thêm 15 phút sử dụng'
                        ) : (
                          <span className="inline-flex flex-wrap items-baseline gap-x-1.5">
                            <span>Báo chặn nhầm tên miền</span>
                            {item.domain && <span className="font-mono text-sm font-medium text-brand-700">{item.domain}</span>}
                          </span>
                        )}
                      </p>
                    </div>
                  </div>

                  {isPending ? (
                    <div className="mt-4 flex flex-col gap-3">
                      <label htmlFor={`request-message-${item.id}`} className="flex flex-col gap-1.5">
                        <span className="flex items-center justify-between gap-3 text-sm font-medium text-ink">
                          Lời nhắn cho con
                          <span className="text-xs font-normal text-ink-muted">{(messages[item.id] ?? '').length}/500</span>
                        </span>
                        <textarea
                          id={`request-message-${item.id}`}
                          maxLength={500}
                          value={messages[item.id] ?? ''}
                          onChange={(event) => setMessages((current) => ({ ...current, [item.id]: event.target.value }))}
                          placeholder="Viết lời nhắn kèm theo quyết định…"
                          className="glass-input min-h-24 resize-y rounded-control px-3.5 py-2.5 text-base text-ink outline-none transition placeholder:text-ink-muted focus:ring-4 focus:ring-brand-200/60"
                        />
                      </label>
                      <div className="flex flex-wrap justify-end gap-2">
                        <Button
                          variant="secondary"
                          disabled={mutation.isPending}
                          loading={isSubmitting && mutation.variables?.approve === false}
                          onClick={() => mutation.mutate({ id: item.id, approve: false })}
                        >
                          <X aria-hidden="true" className="size-4" />
                          Từ chối
                        </Button>
                        <Button
                          disabled={mutation.isPending}
                          loading={isSubmitting && mutation.variables?.approve === true}
                          onClick={() => mutation.mutate({ id: item.id, approve: true })}
                        >
                          <Check aria-hidden="true" className="size-4" />
                          Duyệt yêu cầu
                        </Button>
                      </div>
                    </div>
                  ) : (
                    item.message && (
                      <div className="mt-4 flex items-start gap-2.5 rounded-control bg-brand-50/70 p-3.5 text-sm text-ink ring-1 ring-inset ring-brand-100/70">
                        <MessageCircle aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-brand-700" />
                        <p className="min-w-0 break-words">
                          <span className="font-medium">Lời nhắn: </span>
                          {item.message}
                        </p>
                      </div>
                    )
                  )}
                </Card>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
