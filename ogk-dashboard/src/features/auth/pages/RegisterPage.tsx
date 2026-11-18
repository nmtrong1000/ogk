import { Link, Navigate } from 'react-router-dom'
import { register } from '../api.ts'
import AuthForm from '../components/AuthForm.tsx'
import AuthShell from '../components/AuthShell.tsx'
import { useMe } from '../hooks/useMe.ts'

export default function RegisterPage() {
  const me = useMe()
  if (me.data) return <Navigate to="/" replace />
  return (
    <AuthShell
      title="Tạo tài khoản phụ huynh"
      subtitle="Quản lý thời gian dùng máy tính của con."
      footer={
        <>
          Đã có tài khoản? <Link to="/login">Đăng nhập</Link>
        </>
      }
    >
      <AuthForm mode="register" submit={register} />
    </AuthShell>
  )
}
