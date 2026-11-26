import { NavLink, useLocation } from 'react-router-dom'
import { cn } from '@/shared/utils/cn.ts'

const pages = [
  { label: 'Thời gian dùng máy', path: 'screentime' },
  { label: 'Ứng dụng', path: 'apps' },
  { label: 'Lọc website', path: 'webfilter' },
  { label: 'Chính sách', path: 'policy' },
  { label: 'Báo cáo', path: 'reports' },
  { label: 'Dữ liệu', path: 'data' },
]

export default function ChildPageNavigation() {
  const { pathname } = useLocation()
  const match = pathname.match(/^\/children\/(\d+)(?:\/([^/]+))?$/)
  if (!match) return null

  const [, id, page] = match
  return (
    <nav aria-label="Trang của trẻ" className="glass mb-5 flex flex-wrap gap-1 rounded-glass p-2 text-sm font-medium">
      {pages.map(({ label, path }) => (
        <NavLink
          key={path}
          to={`/children/${id}/${path}`}
          className={({ isActive }) =>
            cn(
              'rounded-control px-2.5 py-1.5 transition-colors',
              isActive ? 'bg-white/75 text-brand-700 shadow-control' : 'text-ink-muted hover:bg-white/60 hover:text-ink',
            )
          }
          aria-current={page === path ? 'page' : undefined}
        >
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
