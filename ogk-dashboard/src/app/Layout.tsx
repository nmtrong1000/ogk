import { Outlet } from 'react-router-dom'

export default function Layout() {
  return (
    <>
      <header className="header">
        <div className="container">OGK</div>
      </header>
      <main className="container">
        <Outlet />
      </main>
    </>
  )
}
