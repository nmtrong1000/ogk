/*
 * Another parent's child returns 404 from every call, so the page only says not found.
 */
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'
import { ApiError } from '@/shared/api/client.ts'
import {
  getPolicy,
  getPolicyChild,
  listPolicyVersions,
  policyChildKey,
  policyKey,
  policyVersionsKey,
} from '@/shared/api/policy.ts'
import { Alert, Card, ChildPageHeader, Spinner } from '@/shared/components/index.ts'
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
      <ChildPageHeader
        title="Chính sách"
        icon={ShieldCheck}
        description={
          <>
            Luật đang áp cho {child.data?.name ?? 'con'}. Máy của con nhận phiên bản mới ở lần đồng bộ tiếp theo, trong
            khoảng một phút.
          </>
        }
      />
      <PolicySummary policy={policy.data} />
      {versions.isError && <Alert tone="error">{policyErrorMessage(versions.error)}</Alert>}
      {versions.isPending && <Spinner />}
      {versions.data && <VersionHistory versions={versions.data} />}
    </div>
  )
}
