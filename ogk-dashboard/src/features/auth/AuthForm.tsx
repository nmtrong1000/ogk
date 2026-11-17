import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import type { Account } from '../../shared/types/auth.ts'
import type { Credentials } from './api.ts'
import { errorMessage } from './messages.ts'
import { switchSession } from './useMe.ts'

export const MIN_PASSWORD_LENGTH = 10

/** Chỉ cho phép quay lại đường nội bộ, tránh chuyển hướng ra trang ngoài. */
function safeNext(next: string | null, account: Account): string {
  if (next && next.startsWith('/') && !next.startsWith('//')) return next
  return account.role === 'admin' ? '/admin/accounts' : '/'
}

type Props = {
  mode: 'login' | 'register'
  submit: (body: Credentials) => Promise<Account>
}

export default function AuthForm({ mode, submit }: Props) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: submit,
    onSuccess: (account) => {
      switchSession(queryClient, account)
      navigate(safeNext(params.get('next'), account), { replace: true })
    },
  })

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    setLocalError(null)
    if (mode === 'register') {
      if (password.length < MIN_PASSWORD_LENGTH) return setLocalError('Mật khẩu phải có ít nhất 10 ký tự')
      if (password !== confirm) return setLocalError('Hai lần nhập mật khẩu không khớp')
    }
    mutation.mutate({ email, password })
  }

  const error = localError ?? (mutation.isError ? errorMessage(mutation.error) : null)

  return (
    <form className="form" onSubmit={onSubmit} noValidate>
      <label>
        Email
        <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label>
        Mật khẩu
        <input
          type="password"
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </label>
      {mode === 'register' && (
        <label>
          Nhập lại mật khẩu
          <input
            type="password"
            autoComplete="new-password"
            required
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
          <small>Ít nhất {MIN_PASSWORD_LENGTH} ký tự.</small>
        </label>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <button type="submit" className="button" disabled={mutation.isPending}>
        {mode === 'login' ? 'Đăng nhập' : 'Đăng ký'}
      </button>
    </form>
  )
}
