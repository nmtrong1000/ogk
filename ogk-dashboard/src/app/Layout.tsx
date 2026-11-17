import { Link, Outlet } from 'react-router-dom'
import { LogoutButton, useMe } from '../features/auth/index.ts'

export default function Layout() {
  const { data: me } = useMe()
  return (
    <>
      <header className="header">
        <div className="container header-row">
          <Link to="/" className="brand">
            OGK
          </Link>
          {me && (
            <nav className="nav">
              {me.role === 'admin' && <Link to="/admin/accounts">Tài khoản</Link>}
              <span className="muted">{me.email}</span>
              <LogoutButton />
            </nav>
          )}
        </div>
      </header>
      <main className="container">
        <Outlet />
      </main>
    </>
  )
}
