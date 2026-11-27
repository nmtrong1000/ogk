import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
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

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('vi-VN')
}

export default function AdminAccountsPage() {
  const queryClient = useQueryClient()
  const [lockedOnly, setLockedOnly] = useState(true)
  const accounts = useQuery({
    queryKey: ['admin', 'accounts', { lockedOnly }],
    queryFn: () => listAccounts(lockedOnly),
  })
  const unlock = useMutation({
    mutationFn: unlockAccount,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'accounts'] }),
  })

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Tài khoản phụ huynh</h1>
        <p className="mt-1 text-ink-muted">Mở khóa tài khoản bị khóa do nhập sai mật khẩu nhiều lần.</p>
      </div>
      <Card
        title="Danh sách"
        actions={
          <Checkbox
            label="Chỉ tài khoản đang khóa"
            checked={lockedOnly}
            onChange={(e) => setLockedOnly(e.target.checked)}
          />
        }
      >
        <div className="flex flex-col gap-4">
          {unlock.isError && <Alert tone="error">{errorMessage(unlock.error)}</Alert>}
          {accounts.isPending && (
            <div className="grid place-items-center py-8">
              <Spinner />
            </div>
          )}
          {accounts.isError && <Alert tone="error">{errorMessage(accounts.error)}</Alert>}
          {accounts.data?.length === 0 && (
            <EmptyState message={lockedOnly ? 'Không có tài khoản nào đang bị khóa.' : 'Chưa có tài khoản phụ huynh nào.'} />
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
                      <Td className="font-medium">{account.email}</Td>
                      <Td>
                        {locked ? (
                          <div className="flex flex-col items-start gap-1">
                            <Badge tone="danger">Đang khóa</Badge>
                            <span className="text-xs text-ink-muted">đến {formatDateTime(lockedUntil)}</span>
                          </div>
                        ) : (
                          <Badge tone="success">Hoạt động</Badge>
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
