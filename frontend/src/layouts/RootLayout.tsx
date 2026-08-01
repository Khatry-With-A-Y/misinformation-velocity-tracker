import { Link, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { AppProvider } from '../context/AppContext'
import { Notification } from '../components/ui/Notification'
import { ThemeToggle } from '../components/ui/ThemeToggle'
import { BrandMark } from '../components/ui/BrandMark'
import { useAuth } from '../context/AuthContext'
import { Button } from '../components/ui/Button'

const publicNavLinks = [
  { to: '/', label: 'Home' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/about', label: 'About' },
] as const

function Navigation() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, logout } = useAuth()
  const linkBase =
    'rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
  const activeLink = 'bg-secondary text-foreground'

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-card transition-colors">
      <nav className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="flex h-14 items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-6">
            <Link
              to="/"
              className="flex shrink-0 items-center gap-2 rounded-md font-semibold tracking-tight text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <BrandMark className="h-5 w-5 text-primary" />
              <span>GuffGuard</span>
            </Link>
            <div className="hidden items-center gap-1 sm:flex">
              {publicNavLinks.map(({ to, label }) => (
                <Link
                  key={to}
                  to={to}
                  aria-current={location.pathname === to ? 'page' : undefined}
                  className={location.pathname === to ? `${linkBase} ${activeLink}` : linkBase}
                >
                  {label}
                </Link>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            {isAuthenticated ? (
              <Button variant="ghost" size="sm" onClick={handleLogout}>
                Logout
              </Button>
            ) : (
              <Link
                to="/login"
                aria-current={location.pathname === '/login' ? 'page' : undefined}
                className={
                  location.pathname === '/login' ? `${linkBase} ${activeLink}` : linkBase
                }
              >
                Login
              </Link>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1 overflow-x-auto pb-2 sm:hidden">
          {publicNavLinks.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              aria-current={location.pathname === to ? 'page' : undefined}
              className={location.pathname === to ? `${linkBase} ${activeLink}` : linkBase}
            >
              {label}
            </Link>
          ))}
        </div>
      </nav>
    </header>
  )
}

export default function RootLayout() {
  const currentYear = new Date().getFullYear()

  return (
    <AppProvider>
      <div className="flex min-h-screen flex-col bg-background text-foreground transition-colors">
        <Navigation />
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 lg:py-10">
          <Outlet />
        </main>
        <footer className="mt-auto border-t border-border bg-card transition-colors">
          <div className="mx-auto flex max-w-7xl flex-col gap-1 px-4 py-5 text-sm sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <p className="flex items-center gap-2 font-medium text-foreground">
              <BrandMark className="h-4 w-4 text-primary" />
              GuffGuard
            </p>
            <p className="text-muted-foreground">
              {currentYear}. Built for journalists and fact-checkers in Nepal.
            </p>
          </div>
        </footer>
        <Notification />
      </div>
    </AppProvider>
  )
}
