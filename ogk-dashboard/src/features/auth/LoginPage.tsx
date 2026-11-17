import { Link, Navigate } from 'react-router-dom'
import { login } from './api.ts'
import AuthForm from './AuthForm.tsx'
import { useMe } from './useMe.ts'

export default function LoginPage() {
  const me = useMe()
  if (me.data) return <Navigate to="/" replace />
  return (
    <section className="auth">
      <h1>Đăng nhập</h1>
      <AuthForm mode="login" submit={login} />
      <p>
        Chưa có tài khoản? <Link to="/register">Đăng ký</Link>
      </p>
    </section>
  )
}
