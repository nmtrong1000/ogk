import { Link } from 'react-router-dom'
import { Card } from '@/shared/components/index.ts'

export default function NotFoundPage() {
  return (
    <Card strong className="mx-auto max-w-md text-center">
      <p className="bg-linear-to-br from-brand-400 to-brand-600 bg-clip-text text-6xl font-bold text-transparent">404</p>
      <h1 className="mt-3 text-xl font-bold text-ink">Không tìm thấy trang</h1>
      <p className="mt-2 text-ink-muted">Đường dẫn không tồn tại hoặc đã bị đổi.</p>
      <p className="mt-5">
        <Link to="/">Về trang tổng quan</Link>
      </p>
    </Card>
  )
}
