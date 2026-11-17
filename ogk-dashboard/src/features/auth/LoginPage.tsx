import { Link, Navigate } from 'react-router-dom'
import { login } from './api.ts'
import AuthForm from './AuthForm.tsx'
import AuthShell from './AuthShell.tsx'
import { useMe } from './useMe.ts'

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
