/*
 * Query keys of other features are written out here because features may not import each other; they must
 * match the keys in reports, requests and commands so those pages refetch after a wipe.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '@/shared/api/client.ts'
import { getPolicyChild, policyChildKey, policyVersionsKey } from '@/shared/api/policy.ts'
import { Alert, Button, Card, Dialog } from '@/shared/components/index.ts'
import type { WipeResult } from '@/shared/types/retention.ts'
import { wipeChildData } from '@/features/retention/api.ts'
import { errorMessage } from '@/features/retention/utils/messages.ts'

const RETENTION_DAYS = 90

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

function doneMessage(result: WipeResult): string {
  if (result.devices_notified === 0) return 'Đã xóa dữ liệu trên máy chủ. Con chưa được gán vào máy tính nào.'
  return `Đã xóa dữ liệu trên máy chủ và gửi lệnh xóa tới ${result.devices_notified} máy tính của con. Máy đang tắt sẽ xóa khi bật lại và kết nối.`
}

export default function RetentionPage() {
  const id = parseId(useParams().id)
  if (id === null) return <NotFound />
  return <Retention id={id} />
}

function Retention({ id }: { id: number }) {
  const queryClient = useQueryClient()
  const [confirming, setConfirming] = useState(false)
  const child = useQuery({ queryKey: policyChildKey(id), queryFn: () => getPolicyChild(id) })
  const wipe = useMutation({
    mutationFn: () => wipeChildData(id),
    onSuccess: () => {
      setConfirming(false)
      queryClient.invalidateQueries({ queryKey: ['reports', id] })
      queryClient.invalidateQueries({ queryKey: ['requests'] })
      queryClient.invalidateQueries({ queryKey: ['commands'] })
      queryClient.invalidateQueries({ queryKey: policyVersionsKey(id) })
    },
  })

  if (child.error instanceof ApiError && child.error.status === 404) return <NotFound />
  const name = child.data?.name ?? 'con'

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Dữ liệu của con</h1>
        <p className="mt-1 text-ink-muted">
          Lịch sử dùng máy, ứng dụng, website, yêu cầu và lệnh được tự động xóa sau {RETENTION_DAYS} ngày trên máy chủ
          và trên máy tính của con.
        </p>
      </div>

      {wipe.isSuccess && <Alert tone="success">{doneMessage(wipe.data)}</Alert>}

      <Card title="Xóa toàn bộ dữ liệu">
        <div className="flex flex-col items-start gap-4">
          <p className="text-ink-muted">
            Xóa ngay toàn bộ lịch sử của {name}: thời gian dùng máy, ứng dụng và website đã mở, yêu cầu, lệnh và các
            phiên bản chính sách cũ. Thông tin của con, chính sách đang áp dụng và máy tính đã gán vẫn được giữ để tiếp
            tục quản lý.
          </p>
          <Button
            variant="danger"
            disabled={child.isPending}
            onClick={() => {
              wipe.reset()
              setConfirming(true)
            }}
          >
            Xóa toàn bộ dữ liệu của con tôi
          </Button>
        </div>
      </Card>

      <Dialog
        open={confirming}
        title={`Xóa toàn bộ dữ liệu của ${name}?`}
        onClose={() => !wipe.isPending && setConfirming(false)}
        actions={
          <>
            <Button variant="ghost" disabled={wipe.isPending} onClick={() => setConfirming(false)}>
              Hủy
            </Button>
            <Button variant="danger" loading={wipe.isPending} onClick={() => wipe.mutate()}>
              Xóa
            </Button>
          </>
        }
      >
        <p>
          Lịch sử của con sẽ bị xóa trên máy chủ và trên máy tính của con, không thể khôi phục. Thời gian đã dùng hôm
          nay cũng được tính lại từ đầu.
        </p>
        {wipe.isError && (
          <Alert tone="error" className="mt-4">
            {errorMessage(wipe.error)}
          </Alert>
        )}
      </Dialog>
    </div>
  )
}
