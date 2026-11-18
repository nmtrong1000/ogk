import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../../shared/api/client.ts'
import { Alert, Button, Card, Dialog, Spinner } from '../../shared/components/index.ts'
import type { Child, ChildInput } from '../../shared/types/family.ts'
import { childKey, childrenKey, deleteChild, getChild, updateChild } from './api.ts'
import ChildForm from './ChildForm.tsx'
import { errorMessage } from './messages.ts'
import { ageFrom } from './year.ts'

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

function parseId(value: string | undefined): number | null {
  return value && /^\d+$/.test(value) ? Number(value) : null
}

export default function ChildDetailPage() {
  const id = parseId(useParams().id)
  if (id === null) return <NotFound />
  return <ChildDetail id={id} />
}

function ChildDetail({ id }: { id: number }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [saved, setSaved] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const child = useQuery({ queryKey: childKey(id), queryFn: () => getChild(id) })

  const update = useMutation({
    mutationFn: (body: ChildInput) => updateChild(id, body),
    onSuccess: (data: Child) => {
      setSaved(true)
      queryClient.setQueryData(childKey(id), data)
      queryClient.invalidateQueries({ queryKey: childrenKey, exact: true })
    },
  })
  const remove = useMutation({
    mutationFn: () => deleteChild(id),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: childKey(id) })
      queryClient.invalidateQueries({ queryKey: childrenKey, exact: true })
      navigate('/children', { replace: true })
    },
  })

  if (child.isPending) {
    return (
      <div className="grid place-items-center py-20">
        <Spinner size="lg" />
      </div>
    )
  }
  // Trẻ của phụ huynh khác cũng trả 404 nên trang chỉ báo không tìm thấy.
  if (child.error instanceof ApiError && child.error.status === 404) return <NotFound />
  if (child.isError) return <Alert tone="error">{errorMessage(child.error)}</Alert>

  const data = child.data
  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="text-sm">
          <Link to="/children">← Các con</Link>
        </p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-ink sm:text-3xl">{data.name}</h1>
        <p className="mt-1 text-ink-muted">
          Sinh năm {data.birth_year} ({ageFrom(data.birth_year)} tuổi)
        </p>
      </div>

      <Card title="Sửa thông tin">
        <div className="flex flex-col gap-4">
          {saved && !update.isError && <Alert tone="success">Đã lưu thay đổi.</Alert>}
          <ChildForm
            key={data.updated_at}
            initial={{ name: data.name, birth_year: data.birth_year }}
            submitLabel="Lưu"
            pending={update.isPending}
            error={update.error}
            onSubmit={(body) => {
              setSaved(false)
              update.mutate(body)
            }}
            secondaryAction={
              <Button
                variant="ghost"
                className="text-rose-600 hover:bg-rose-50/60"
                disabled={update.isPending}
                onClick={() => {
                  remove.reset()
                  setConfirming(true)
                }}
              >
                Xóa
              </Button>
            }
          />
        </div>
      </Card>

      <Dialog
        open={confirming}
        title={`Xóa ${data.name}?`}
        onClose={() => !remove.isPending && setConfirming(false)}
        actions={
          <>
            <Button variant="ghost" disabled={remove.isPending} onClick={() => setConfirming(false)}>
              Hủy
            </Button>
            <Button variant="danger" loading={remove.isPending} onClick={() => remove.mutate()}>
              Xóa
            </Button>
          </>
        }
      >
        <p>Thông tin của con sẽ bị xóa khỏi tài khoản và không thể khôi phục.</p>
        {remove.isError && (
          <Alert tone="error" className="mt-4">
            {errorMessage(remove.error)}
          </Alert>
        )}
      </Dialog>
    </div>
  )
}
