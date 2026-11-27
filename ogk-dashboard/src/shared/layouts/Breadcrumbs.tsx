import { ChevronRight } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/shared/utils/cn.ts'

type Crumb = { label: string; to?: string }

const PAGE_LABELS: Record<string, string> = {
  policy: 'Chính sách',
  screentime: 'Thời gian sử dụng',
  apps: 'Ứng dụng',
  webfilter: 'Lọc web',
  reports: 'Báo cáo',
  data: 'Dữ liệu',
}

function breadcrumbs(pathname: string): Crumb[] {
  if (pathname === '/') return [{ label: 'Trang chủ' }]

  const home: Crumb = { label: 'Tổng quan', to: '/' }
  if (pathname === '/children/requests') {
    return [home, { label: 'Các con', to: '/children' }, { label: 'Yêu cầu của con' }]
  }
  if (/^\/devices\/[^/]+\/alerts$/.test(pathname)) {
    return [home, { label: 'Thiết bị', to: '/devices' }, { label: 'Cảnh báo' }]
  }
  const child = pathname.match(/^\/children\/([^/]+)(?:\/([^/]+))?$/)
  if (child) {
    const [, id, page] = child
    const list = { label: 'Các con', to: '/children' }
    const profile = { label: `Trẻ ${id}`, to: `/children/${id}` }
    return [
      home,
      list,
      page ? profile : { label: `Trẻ ${id}` },
      ...(page ? [{ label: PAGE_LABELS[page] ?? `Trẻ ${id}` }] : []),
    ]
  }

  if (pathname === '/children') return [home, { label: 'Các con' }]
  if (pathname === '/devices') return [home, { label: 'Thiết bị' }]
  if (pathname === '/devices/add') return [home, { label: 'Thiết bị', to: '/devices' }, { label: 'Thêm thiết bị' }]
  if (pathname === '/audit') return [home, { label: 'Nhật ký' }]
  if (pathname === '/admin/accounts') return [home, { label: 'Quản trị' }, { label: 'Tài khoản phụ huynh' }]
  if (pathname === '/admin/webfilter') return [home, { label: 'Quản trị' }, { label: 'Phân loại web' }]
  if (pathname === '/child-view/start') return [{ label: 'Chế độ xem trẻ', to: '/child-view' }, { label: 'Bắt đầu' }]
  if (pathname === '/child-view') return [{ label: 'Chế độ xem trẻ' }]
  if (pathname === '/design') return [home, { label: 'Design system' }]
  return [home, { label: 'Không tìm thấy trang' }]
}

export default function Breadcrumbs() {
  const { pathname } = useLocation()
  const normalizedPath = pathname.replace(/\/+$/, '') || '/'
  const items = breadcrumbs(normalizedPath)

  return (
    <nav aria-label="Đường dẫn" className="mb-4 sm:mb-5">
      <ol className="flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-1 text-sm">
        {items.map((item, index) => {
          const current = index === items.length - 1
          return (
            <li key={`${item.label}-${index}`} className="flex min-w-0 items-center gap-1.5">
              {index > 0 && <ChevronRight aria-hidden="true" className="size-4 shrink-0 text-ink-muted" />}
              {item.to && !current ? (
                <Link to={item.to} className="truncate text-ink-muted no-underline hover:text-brand-700">
                  {item.label}
                </Link>
              ) : (
                <span
                  aria-current={current ? 'page' : undefined}
                  className={cn('truncate', current ? 'font-medium text-ink' : 'text-ink-muted')}
                >
                  {item.label}
                </span>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
