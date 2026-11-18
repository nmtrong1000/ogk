/*
 * Shared login/register form. The `next` redirect only allows internal paths, never an external site.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Alert, Button, TextField } from '@/shared/components/index.ts'
import type { Account } from '@/shared/types/auth.ts'
import type { Credentials } from '@/features/auth/api.ts'
import { errorMessage } from '@/features/auth/utils/messages.ts'
import { switchSession } from '@/features/auth/hooks/useMe.ts'

export const MIN_PASSWORD_LENGTH = 10

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
    <form className="flex flex-col gap-4" onSubmit={onSubmit} noValidate>
      <TextField
        label="Email"
        type="email"
        autoComplete="email"
        required
        placeholder="ban@example.com"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <TextField
        label="Mật khẩu"
        type="password"
        autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
        required
        hint={mode === 'register' ? `Ít nhất ${MIN_PASSWORD_LENGTH} ký tự.` : undefined}
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      {mode === 'register' && (
        <TextField
          label="Nhập lại mật khẩu"
          type="password"
          autoComplete="new-password"
          required
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
        />
      )}
      {error && <Alert tone="error">{error}</Alert>}
      <Button type="submit" size="lg" block loading={mutation.isPending} className="mt-1">
        {mode === 'login' ? 'Đăng nhập' : 'Tạo tài khoản'}
      </Button>
    </form>
  )
}
