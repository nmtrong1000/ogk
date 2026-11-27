import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { CircleCheck, LockKeyhole, Mail, UnlockKeyhole, UsersRound } from 'lucide-react'
import { formatDateTime } from '@/shared/utils/dateTime.ts'
import { useToast } from '@/shared/components/ToastContext.ts'
import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  EmptyState,
  Spinner,
  Table,
  TableBody,
  TableHead,
  TableRow,
  Td,
  Th,
} from '@/shared/components/index.ts'
import { listAccounts, unlockAccount } from '@/features/auth/api.ts'
import { errorMessage } from '@/features/auth/utils/messages.ts'

export default function AdminAccountsPage() {
  const queryClient = useQueryClient()
  const showToast = useToast()
  const [lockedOnly, setLockedOnly] = useState(false)
  const accounts = useQuery({
    queryKey: ['admin', 'accounts', { lockedOnly }],
    queryFn: () => listAccounts(lockedOnly),
  })
  const unlock = useMutation({
    mutationFn: unlockAccount,
    onSuccess: (account) => {
      if (lockedOnly) setLockedOnly(false)
      showToast({ tone: 'success', message: `Đã mở khóa ${account.email}. Đang hiển thị tất cả tài khoản.` })
      return queryClient.invalidateQueries({ queryKey: ['admin', 'accounts'] })
    },
    onError: (error) => showToast({ tone: 'error', message: errorMessage(error) }),
  })

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Tài khoản phụ huynh</h1>
        <p className="mt-1 text-ink-muted">
          Tài khoản tự khóa sau 5 lần nhập sai mật khẩu. Admin có thể mở khóa tại đây.
        </p>
      </div>
      <Card
        strong
        title="Danh sách tài khoản"
        description="Theo dõi trạng thái đăng nhập và mở khóa tài khoản phụ huynh."
        actions={
          <div className="flex flex-wrap items-center gap-3">
            {accounts.data && (
              <Badge tone={lockedOnly ? 'warning' : 'brand'}>
                <UsersRound aria-hidden="true" className="size-3.5" />
                {accounts.data.length} {lockedOnly ? 'đang khóa' : 'tài khoản'}
              </Badge>
            )}
            <Checkbox
              label="Chỉ tài khoản đang khóa"
              checked={lockedOnly}
              onChange={(e) => setLockedOnly(e.target.checked)}
            />
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          {accounts.isPending && (
            <div className="grid place-items-center py-8">
              <Spinner />
            </div>
          )}
          {accounts.isError && <Alert tone="error">{errorMessage(accounts.error)}</Alert>}
          {accounts.data?.length === 0 && (
            <EmptyState
              icon={lockedOnly ? CircleCheck : UsersRound}
              message={lockedOnly ? 'Không có tài khoản nào đang bị khóa.' : 'Chưa có tài khoản phụ huynh nào.'}
              description={lockedOnly ? 'Các tài khoản hiện có vẫn có thể đăng nhập bình thường.' : undefined}
            />
          )}
          {accounts.data && accounts.data.length > 0 && (
            <Table>
              <TableHead>
                <tr>
                  <Th>Email</Th>
                  <Th>Trạng thái</Th>
                  <Th>
                    <span className="sr-only">Thao tác</span>
                  </Th>
                </tr>
              </TableHead>
              <TableBody>
                {accounts.data.map((account) => {
                  const lockedUntil = account.locked_until
                  const locked = lockedUntil !== null && new Date(lockedUntil) > new Date()
                  return (
                    <TableRow key={account.id}>
                      <Td>
                        <span className="inline-flex min-w-0 items-center gap-2.5 font-medium text-ink">
                          <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-brand-100/80 text-brand-700">
                            <Mail aria-hidden="true" className="size-4" />
                          </span>
                          <span className="break-all">{account.email}</span>
                        </span>
                      </Td>
                      <Td>
                        {locked ? (
                          <div className="flex flex-col items-start gap-1.5">
                            <Badge tone="danger">
                              <LockKeyhole aria-hidden="true" className="size-3.5" />
                              Đang khóa
                            </Badge>
                            <span className="text-sm text-ink-muted">Đến {formatDateTime(lockedUntil)}</span>
                          </div>
                        ) : (
                          <Badge tone="success">
                            <CircleCheck aria-hidden="true" className="size-3.5" />
                            Hoạt động
                          </Badge>
                        )}
                      </Td>
                      <Td className="text-right">
                        {locked && (
                          <Button
                            size="sm"
                            variant="secondary"
                            loading={unlock.isPending && unlock.variables === account.id}
                            disabled={unlock.isPending}
                            onClick={() => unlock.mutate(account.id)}
                          >
                            <UnlockKeyhole aria-hidden="true" className="size-4" />
                            Mở khóa
                          </Button>
                        )}
                      </Td>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </div>
      </Card>
    </div>
  )
}
