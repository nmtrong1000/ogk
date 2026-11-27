import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '@/shared/api/client.ts'
import { Alert, Card, Spinner } from '@/shared/components/index.ts'
import { childKey, getChild } from '@/features/family/api.ts'
import ChildDevices from '@/features/family/components/ChildDevices.tsx'
import { errorMessage } from '@/features/family/utils/messages.ts'
import { ageFrom } from '@/features/family/utils/year.ts'

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
  const child = useQuery({ queryKey: childKey(id), queryFn: () => getChild(id) })

  if (child.isPending) {
    return (
      <div className="grid place-items-center py-20">
        <Spinner size="lg" />
      </div>
    )
  }
  if (child.error instanceof ApiError && child.error.status === 404) return <NotFound />
  if (child.isError) return <Alert tone="error">{errorMessage(child.error)}</Alert>

  const data = child.data
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">{data.name}</h1>
        <p className="mt-1 text-ink-muted">
          Sinh năm {data.birth_year} ({ageFrom(data.birth_year)} tuổi)
        </p>
      </div>

      <ChildDevices childId={id} />
    </div>
  )
}
