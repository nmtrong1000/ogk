import { Link, Navigate } from 'react-router-dom'
import { register } from './api.ts'
import AuthForm from './AuthForm.tsx'
import { useMe } from './useMe.ts'

export default function RegisterPage() {
  const me = useMe()
  if (me.data) return <Navigate to="/" replace />
  return (
    <section className="auth">
      <h1>Đăng ký tài khoản phụ huynh</h1>
      <AuthForm mode="register" submit={register} />
      <p>
        Đã có tài khoản? <Link to="/login">Đăng nhập</Link>
      </p>
    </section>
  )
}
