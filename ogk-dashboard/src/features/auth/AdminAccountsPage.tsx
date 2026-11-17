import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { listAccounts, unlockAccount } from './api.ts'
import { errorMessage } from './messages.ts'

function formatDateTime(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString('vi-VN') : '—'
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
    <section>
      <h1>Tài khoản phụ huynh</h1>
      <label className="checkbox">
        <input type="checkbox" checked={lockedOnly} onChange={(e) => setLockedOnly(e.target.checked)} />
        Chỉ hiện tài khoản đang bị khóa
      </label>
      {unlock.isError && <p className="error">{errorMessage(unlock.error)}</p>}
      {accounts.isPending && <p>Đang tải...</p>}
      {accounts.isError && <p className="error">{errorMessage(accounts.error)}</p>}
      {accounts.data?.length === 0 && <p>Không có tài khoản nào.</p>}
      {accounts.data && accounts.data.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Khóa đến</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {accounts.data.map((account) => {
                const locked = account.locked_until !== null && new Date(account.locked_until) > new Date()
                return (
                  <tr key={account.id}>
                    <td>{account.email}</td>
                    <td>{locked ? formatDateTime(account.locked_until) : 'Không khóa'}</td>
                    <td>
                      {locked && (
                        <button
                          type="button"
                          className="button"
                          disabled={unlock.isPending}
                          onClick={() => unlock.mutate(account.id)}
                        >
                          Mở khóa
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
