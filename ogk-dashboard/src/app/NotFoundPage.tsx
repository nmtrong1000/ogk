import { Link } from 'react-router-dom'
import AuthShell from '@/features/auth/components/AuthShell.tsx'

export default function NotFoundPage() {
  return (
    <AuthShell
      title="Không tìm thấy trang"
      subtitle="Đường dẫn này không tồn tại hoặc đã được thay đổi."
      footer={<Link to="/">Về trang chủ</Link>}
    >
      <div className="py-3 text-center">
        <p className="bg-linear-to-br from-brand-400 to-brand-600 bg-clip-text text-6xl font-bold text-transparent">
          404
        </p>
        <p className="mt-2 text-sm text-ink-muted">Hãy kiểm tra lại địa chỉ trang bạn vừa mở.</p>
      </div>
    </AuthShell>
  )
}
