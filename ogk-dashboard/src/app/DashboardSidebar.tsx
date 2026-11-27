import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  ChevronDown,
  ClipboardList,
  FileClock,
  Globe,
  House,
  Laptop,
  LockKeyhole,
  MonitorCog,
  UsersRound,
  UserRoundCog,
  type LucideIcon,
} from 'lucide-react'
import type { Role } from '@/shared/types/auth.ts'
import { cn } from '@/shared/utils/cn.ts'

type MenuItem = { label: string; to: string; icon: LucideIcon; end?: boolean }
type MenuGroup = { label: string; icon: LucideIcon; items: MenuItem[] }

function menuForRole(role: Role, pathname: string): MenuGroup[] {
  if (role === 'admin') {
    return [
      {
        label: 'Quản trị',
        icon: UserRoundCog,
        items: [
          { label: 'Tài khoản', to: '/admin/accounts', icon: UsersRound },
          { label: 'Phân loại web', to: '/admin/webfilter', icon: Globe },
        ],
      },
    ]
  }

  const childId = pathname.match(/^\/children\/(\d+)\/(?:policy|screentime|apps|webfilter|reports|data)$/)?.[1]
  const groups: MenuGroup[] = [
    {
      label: 'Gia đình',
      icon: UsersRound,
      items: [
        { label: 'Các con', to: '/children', icon: UsersRound, end: true },
        { label: 'Yêu cầu của con', to: '/children/requests', icon: ClipboardList },
      ],
    },
    {
      label: 'Thiết bị',
      icon: Laptop,
      items: [
        { label: 'Danh sách thiết bị', to: '/devices', icon: Laptop, end: true },
        { label: 'Thêm thiết bị', to: '/devices/add', icon: MonitorCog },
      ],
    },
  ]

  if (childId) {
    groups.splice(1, 0, {
      label: 'Cấu hình trẻ',
      icon: LockKeyhole,
      items: [
        { label: 'Chính sách', to: `/children/${childId}/policy`, icon: LockKeyhole },
        { label: 'Thời gian sử dụng', to: `/children/${childId}/screentime`, icon: FileClock },
        { label: 'Ứng dụng', to: `/children/${childId}/apps`, icon: MonitorCog },
        { label: 'Lọc web', to: `/children/${childId}/webfilter`, icon: Globe },
        { label: 'Báo cáo', to: `/children/${childId}/reports`, icon: ClipboardList },
        { label: 'Dữ liệu', to: `/children/${childId}/data`, icon: FileClock },
      ],
    })
  }

  return groups
}

type Props = { role?: Role; onNavigate?: () => void }

export default function DashboardSidebar({ role = 'parent', onNavigate }: Props) {
  const { pathname } = useLocation()
  const groups = menuForRole(role, pathname)
  const activeGroup = groups.find(
    (group) =>
      group.items.some(
        (item) => pathname === item.to || (!item.end && pathname.startsWith(`${item.to}/`)),
      ) || (group.label === 'Thiết bị' && pathname.startsWith('/devices/')),
  )?.label
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({})

  function itemClass(isActive: boolean) {
    return cn(
      'flex items-center gap-3 rounded-control px-3 py-2.5 text-sm font-medium no-underline transition-colors',
      isActive ? 'bg-brand-100/80 text-brand-700' : 'text-ink-muted hover:bg-white/60 hover:text-brand-700',
    )
  }

  return (
    <nav aria-label="Menu chính" className="flex flex-col gap-1">
      <NavLink to="/" end onClick={onNavigate} className={({ isActive }) => itemClass(isActive)}>
        <House aria-hidden="true" className="size-5 shrink-0" />
        <span>Tổng quan</span>
      </NavLink>
      <NavLink to="/audit" end onClick={onNavigate} className={({ isActive }) => itemClass(isActive)}>
        <FileClock aria-hidden="true" className="size-5 shrink-0" />
        <span>Nhật ký</span>
      </NavLink>
      {groups.map((group) => {
        const expanded = openGroups[group.label] ?? activeGroup === group.label
        const panelId = `menu-${group.label.replaceAll(' ', '-').toLowerCase()}`
        return (
          <div key={group.label}>
            <button
              type="button"
              aria-expanded={expanded}
              aria-controls={panelId}
              onClick={() => setOpenGroups((current) => ({ ...current, [group.label]: !expanded }))}
              className="flex w-full items-center gap-3 rounded-control px-3 py-2.5 text-left text-sm font-medium text-ink-muted transition-colors hover:bg-white/60 hover:text-brand-700"
            >
              <group.icon aria-hidden="true" className="size-5 shrink-0" />
              <span className="flex-1">{group.label}</span>
              <ChevronDown
                aria-hidden="true"
                className={cn('size-4 shrink-0 transition-transform', expanded && 'rotate-180')}
              />
            </button>
            {expanded && (
              <div id={panelId} className="ml-4 mt-1 flex flex-col gap-1 border-l border-white/70 pl-3">
                {group.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    onClick={onNavigate}
                    className={({ isActive }) => itemClass(isActive)}
                  >
                    <item.icon aria-hidden="true" className="size-4 shrink-0" />
                    <span>{item.label}</span>
                  </NavLink>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </nav>
  )
}
