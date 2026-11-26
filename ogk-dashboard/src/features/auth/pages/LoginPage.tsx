import { Link, Navigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { login } from '@/features/auth/api.ts'
import AuthForm from '@/features/auth/components/AuthForm.tsx'
import AuthShell from '@/features/auth/components/AuthShell.tsx'
import { ME_KEY } from '@/features/auth/hooks/useMe.ts'
import type { Account } from '@/shared/types/auth.ts'

export default function LoginPage() {
  const me = useQueryClient().getQueryData<Account | null>(ME_KEY)
  if (me) return <Navigate to="/" replace />
  return (
    <AuthShell
      title="Đăng nhập"
      subtitle="Chào mừng phụ huynh quay lại OGK."
      footer={
        <>
          Chưa có tài khoản? <Link to="/register">Đăng ký</Link>
        </>
      }
    >
      <AuthForm mode="login" submit={login} />
    </AuthShell>
  )
}
