import { useQuery } from '@tanstack/react-query'
import { ArrowRight, ClipboardList, FileClock, Globe, Laptop, UserRoundCog, UsersRound } from 'lucide-react'
import { Link } from 'react-router-dom'
import { apiFetch } from '@/shared/api/client.ts'
import { Badge, Card, Spinner } from '@/shared/components/index.ts'
import { useMe } from '@/features/auth/hooks/useMe.ts'
import type { Health } from '@/shared/types/health.ts'

const PARENT_QUICK_LINKS = [
  { label: 'Các con', description: 'Quản lý hồ sơ và thiết lập cho trẻ.', to: '/children', icon: UsersRound },
  { label: 'Thiết bị', description: 'Xem thiết bị đã kết nối với gia đình.', to: '/devices', icon: Laptop },
  {
    label: 'Yêu cầu của con',
    description: 'Xem và xử lý yêu cầu từ các con.',
    to: '/children/requests',
    icon: ClipboardList,
  },
]

const ADMIN_QUICK_LINKS = [
  { label: 'Tài khoản', description: 'Quản lý tài khoản phụ huynh.', to: '/admin/accounts', icon: UserRoundCog },
  { label: 'Phân loại web', description: 'Quản lý phân loại tên miền.', to: '/admin/webfilter', icon: Globe },
  { label: 'Nhật ký', description: 'Xem các thay đổi trong hệ thống.', to: '/audit', icon: FileClock },
]

export default function HomePage() {
  const { data: me } = useMe()
  const quickLinks = me?.role === 'admin' ? ADMIN_QUICK_LINKS : PARENT_QUICK_LINKS
  const { data, error, isPending } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiFetch<Health>('/api/health'),
  })

  let status = <Spinner size="sm" label="Đang kiểm tra" />
  if (error) status = <Badge tone="danger">Lỗi: {error.message}</Badge>
  else if (!isPending) status = <Badge tone={data.status === 'ok' ? 'success' : 'warning'}>{data.status}</Badge>

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Tổng quan</h1>
        <p className="mt-1 text-ink-muted">Theo dõi và quản lý việc sử dụng máy tính của con.</p>
      </div>

      <Card strong title="Chào mừng đến OGK" description="Chọn một mục để bắt đầu quản lý gia đình của bạn.">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {quickLinks.map(({ label, description, to, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className="glass-input group flex min-w-0 items-center gap-4 rounded-control p-4 no-underline transition-colors hover:bg-white/90"
            >
              <span className="grid size-11 shrink-0 place-items-center rounded-control bg-brand-100/80 text-brand-700">
                <Icon aria-hidden="true" className="size-5" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block font-semibold text-ink">{label}</span>
                <span className="mt-0.5 block text-sm text-ink-muted">{description}</span>
              </span>
              <ArrowRight
                aria-hidden="true"
                className="size-4 shrink-0 text-ink-muted transition-transform group-hover:translate-x-1"
              />
            </Link>
          ))}
        </div>
      </Card>

      <Card title="Trạng thái server" description="Tình trạng kết nối tới OGK-Server.">
        <div className="flex flex-wrap items-center gap-3 text-sm text-ink-muted">
          <span>Kết nối tới OGK-Server</span>
          {status}
        </div>
      </Card>
    </div>
  )
}
