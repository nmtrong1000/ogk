/*
 * Another parent's child returns 404 from every call, so the page only says not found.
 */
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '@/shared/api/client.ts'
import {
  getPolicy,
  getPolicyChild,
  listPolicyVersions,
  policyChildKey,
  policyKey,
  policyVersionsKey,
} from '@/shared/api/policy.ts'
import { Alert, Card, Spinner } from '@/shared/components/index.ts'
import PolicySummary from '@/features/policy/components/PolicySummary.tsx'
import VersionHistory from '@/features/policy/components/VersionHistory.tsx'
import { policyErrorMessage } from '@/features/policy/utils/messages.ts'

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

export default function PolicyPage() {
  const id = parseId(useParams().id)
  if (id === null) return <NotFound />
  return <PolicyOverview id={id} />
}

function PolicyOverview({ id }: { id: number }) {
  const child = useQuery({ queryKey: policyChildKey(id), queryFn: () => getPolicyChild(id) })
  const policy = useQuery({ queryKey: policyKey(id), queryFn: () => getPolicy(id) })
  const versions = useQuery({ queryKey: policyVersionsKey(id), queryFn: () => listPolicyVersions(id) })

  if (child.isPending || policy.isPending) {
    return (
      <div className="grid place-items-center py-20">
        <Spinner size="lg" />
      </div>
    )
  }
  if (policy.error instanceof ApiError && policy.error.status === 404) return <NotFound />
  if (policy.isError) return <Alert tone="error">{policyErrorMessage(policy.error)}</Alert>

  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="text-sm">
          <Link to={`/children/${id}`}>← {child.data?.name ?? 'Thông tin của con'}</Link>
        </p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-ink sm:text-3xl">Chính sách</h1>
        <p className="mt-1 text-ink-muted">
          Luật đang áp cho {child.data?.name ?? 'con'}. Máy của con nhận phiên bản mới ở lần đồng bộ tiếp theo, trong
          khoảng một phút. <Link to={`/children/${id}/screentime`}>Sửa thời gian dùng máy</Link>
        </p>
      </div>
      <PolicySummary policy={policy.data} />
      {versions.isError && <Alert tone="error">{policyErrorMessage(versions.error)}</Alert>}
      {versions.isPending && <Spinner />}
      {versions.data && <VersionHistory versions={versions.data} />}
    </div>
  )
}
