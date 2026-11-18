import { Link, Navigate } from 'react-router-dom'
import { login } from '@/features/auth/api.ts'
import AuthForm from '@/features/auth/components/AuthForm.tsx'
import AuthShell from '@/features/auth/components/AuthShell.tsx'
import { useMe } from '@/features/auth/hooks/useMe.ts'

export default function LoginPage() {
  const me = useMe()
  if (me.data) return <Navigate to="/" replace />
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
