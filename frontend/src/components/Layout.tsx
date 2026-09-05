import { NavLink, Outlet } from 'react-router-dom'
import { HealthStatus } from './HealthStatus'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-2 py-1.5 text-sm font-medium transition-colors sm:px-3 ${
    isActive
      ? 'bg-accent-soft text-accent'
      : 'text-ink-soft hover:bg-accent-soft hover:text-accent'
  }`

export function Layout() {
  return (
    <div className="flex min-h-svh flex-col bg-paper text-ink">
      <header className="border-b border-line bg-raised">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-2 px-4 py-4 sm:px-6">
          <NavLink to="/" className="flex items-baseline gap-2">
            <span className="font-mono text-base font-semibold tracking-tight sm:text-lg">
              ForexMind AI
            </span>
            <span className="hidden text-xs text-ink-faint sm:inline">EUR/USD</span>
          </NavLink>
          <nav className="flex gap-1">
            <NavLink to="/" end className={navLinkClass}>
              Dashboard
            </NavLink>
            <NavLink to="/history" className={navLinkClass}>
              History
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10 sm:px-6">
        <Outlet />
      </main>

      <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-4 py-4 sm:px-6">
        <span className="font-mono text-xs text-ink-faint">
          Analyst, not an autotrader &mdash; every call ships with its reasoning.
        </span>
        <HealthStatus />
      </footer>
    </div>
  )
}
