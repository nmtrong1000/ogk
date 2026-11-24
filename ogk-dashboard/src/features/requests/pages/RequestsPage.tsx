import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Card, Spinner } from '@/shared/components/index.ts'
import { ApiError } from '@/shared/api/client.ts'
import { decideRequest, listRequests, requestsKey, type ChildRequest } from '@/features/requests/api.ts'

function statusLabel(status: ChildRequest['status']) {
  return status === 'pending' ? 'Đang chờ' : status === 'approved' ? 'Đã duyệt' : 'Đã từ chối'
}

function errorText(error: unknown) {
  if (error instanceof ApiError && error.code === 'request_already_decided') return 'Yêu cầu này đã được xử lý.'
  return 'Chưa lưu được quyết định. Vui lòng thử lại.'
}

export default function RequestsPage() {
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: requestsKey, queryFn: listRequests, refetchInterval: 10_000 })
  const [messages, setMessages] = useState<Record<number, string>>({})
  const mutation = useMutation({
    mutationFn: ({ id, approve }: { id: number; approve: boolean }) => decideRequest(id, approve, messages[id] ?? ''),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: requestsKey }),
  })

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Yêu cầu của con</h1>
        <p className="mt-1 text-ink-muted">Xem, phản hồi và gửi lời nhắn cho từng yêu cầu.</p>
      </div>
      {query.isError && <Alert tone="error">Không tải được danh sách yêu cầu.</Alert>}
      {mutation.isError && <Alert tone="error">{errorText(mutation.error)}</Alert>}
      {query.isPending && (
        <div className="grid place-items-center py-12">
          <Spinner />
        </div>
      )}
      {query.data?.length === 0 && (
        <Card>
          <p className="py-6 text-center text-sm text-ink-muted">Chưa có yêu cầu nào.</p>
        </Card>
      )}
      {query.data?.map((item) => (
        <Card
          key={item.id}
          title={item.child_name}
          description={`${statusLabel(item.status)} · ${new Date(item.created_at).toLocaleString('vi-VN')}`}
        >
          <p className="text-sm text-ink">
            {item.type === 'add_time' ? 'Xin thêm giờ' : `Báo chặn nhầm: ${item.domain}`}
          </p>
          {item.status === 'pending' ? (
            <div className="mt-4 flex flex-col gap-3">
              <label className="flex flex-col gap-1.5 text-sm font-medium text-ink">
                Lời nhắn cho con
                <textarea
                  maxLength={500}
                  value={messages[item.id] ?? ''}
                  onChange={(event) => setMessages((current) => ({ ...current, [item.id]: event.target.value }))}
                  className="glass-input min-h-20 rounded-control px-3.5 py-2 text-base"
                />
              </label>
              <div className="flex flex-wrap gap-2">
                <Button disabled={mutation.isPending} onClick={() => mutation.mutate({ id: item.id, approve: true })}>
                  Duyệt
                </Button>
                <Button
                  variant="secondary"
                  disabled={mutation.isPending}
                  onClick={() => mutation.mutate({ id: item.id, approve: false })}
                >
                  Từ chối
                </Button>
              </div>
            </div>
          ) : (
            item.message && <p className="mt-3 text-sm text-ink-muted">Lời nhắn: {item.message}</p>
          )}
        </Card>
      ))}
    </div>
  )
}
