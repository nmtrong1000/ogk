/*
 * Every add or remove sends the whole rule list in one PATCH, so the server's normalized list is what the page
 * shows next; the form is keyed by policy_version so it clears after each save.
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
import type { AppRule, Policy } from '@/shared/types/policy.ts'
import AppRuleForm from '@/features/appcontrol/components/AppRuleForm.tsx'
import AppRuleTable from '@/features/appcontrol/components/AppRuleTable.tsx'
import { appcontrolErrorMessage } from '@/features/appcontrol/utils/messages.ts'

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

export default function AppControlPage() {
  const id = parseId(useParams().id)
  if (id === null) return <NotFound />
  return <AppControl id={id} />
}

function AppControl({ id }: { id: number }) {
  const queryClient = useQueryClient()
  const child = useQuery({ queryKey: policyChildKey(id), queryFn: () => getPolicyChild(id) })
  const policy = useQuery({ queryKey: policyKey(id), queryFn: () => getPolicy(id) })
  const [saved, setSaved] = useState<string | null>(null)
  const save = useMutation({
    mutationFn: (rules: AppRule[]) => updatePolicy(id, { app_rules: rules }),
    onSuccess: (data: Policy) => {
      queryClient.setQueryData(policyKey(id), data)
      queryClient.invalidateQueries({ queryKey: policyVersionsKey(id) })
    },
  })

  if (child.isPending || policy.isPending) {
    return (
      <div className="grid place-items-center py-20">
        <Spinner size="lg" />
      </div>
    )
  }
  if (policy.error instanceof ApiError && policy.error.status === 404) return <NotFound />
  if (policy.isError) return <Alert tone="error">{appcontrolErrorMessage(policy.error)}</Alert>

  const data = policy.data
  const rules = data.app_rules

  function submit(next: AppRule[], message: string) {
    setSaved(null)
    save.mutate(next, { onSuccess: () => setSaved(message) })
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="text-sm">
          <Link to={`/children/${id}`}>← {child.data?.name ?? 'Thông tin của con'}</Link>
        </p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-ink sm:text-3xl">Ứng dụng</h1>
        <p className="mt-1 text-ink-muted">
          Ứng dụng bị chặn sẽ bị đóng ngay khi mở trên máy của {child.data?.name ?? 'con'}, kèm thông báo lý do và người
          đặt luật. Đang áp phiên bản {data.policy_version}. <Link to={`/children/${id}/policy`}>Xem chính sách</Link>
        </p>
      </div>

      {save.error != null && <Alert tone="error">{appcontrolErrorMessage(save.error)}</Alert>}
      {saved && save.error == null && <Alert tone="success">{saved}</Alert>}

      <Card title="Thêm luật" description="Chặn hoặc cho phép một ứng dụng theo tên tệp và mã SHA-256.">
        <AppRuleForm
          key={`app-form-${data.policy_version}`}
          rules={rules}
          pending={save.isPending}
          onAdd={(rule) => submit([...rules, rule], `Đã thêm luật cho ${rule.name}.`)}
        />
      </Card>

      <Card title="Danh sách ứng dụng" description={`${rules.length} luật`}>
        <AppRuleTable
          rules={rules}
          pending={save.isPending}
          onRemove={(rule) =>
            submit(
              rules.filter((r) => r !== rule),
              `Đã xóa luật cho ${rule.name}.`,
            )
          }
        />
      </Card>
    </div>
  )
}
