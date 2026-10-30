import { useEffect, useState } from 'react'
import { ChartColumn, ClipboardList, FileText, Gauge, History, LayoutDashboard, LogOut, Menu, ScanText, User, Users, X } from 'lucide-react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { DisclaimerBanner } from './common'
import Logo from './Logo'

const PATIENT_NAV = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/assess', label: 'New assessment', icon: ClipboardList },
  { to: '/ocr', label: 'Read a report', icon: ScanText },
  { to: '/history', label: 'My history', icon: History },
  { to: '/models', label: 'Model performance', icon: Gauge },
  { to: '/profile', label: 'Profile', icon: User },
]

const ADMIN_NAV = [
  { to: '/admin', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/admin/patients', label: 'Patients', icon: Users },
  { to: '/admin/assessments', label: 'Patient reports', icon: FileText },
  { to: '/admin/analysis', label: 'Disease analysis', icon: ChartColumn },
  { to: '/models', label: 'Model performance', icon: Gauge },
  { to: '/profile', label: 'Profile', icon: User },
]

export default function AppShell() {
  const { user, logout } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const [open, setOpen] = useState(false)

  useEffect(() => setOpen(false), [location.pathname])

  const onLogout = async () => {
    await logout()
    toast.success('Signed out.')
    navigate('/login')
  }

  const isAdmin = user?.role === 'admin'
  const items = isAdmin ? ADMIN_NAV : PATIENT_NAV

  return (
    <div className="shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="topbar">
        <button className="icon-btn nav-toggle" onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-controls="sidebar" aria-label="Toggle navigation">
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
        <Logo to={isAdmin ? '/admin' : '/dashboard'} />
      </header>
      <aside id="sidebar" className={`sidebar ${open ? 'is-open' : ''}`}>
        <div className="sidebar-brand">
          <Logo to={isAdmin ? '/admin' : '/dashboard'} />
          {isAdmin && <span className="role-chip">Administrator</span>}
        </div>
        <nav aria-label="Main">
          <ul>
            {items.map(({ to, label, icon: Icon, end }) => (
              <li key={to}>
                <NavLink to={to} end={end} className={({ isActive }) => `nav-link ${isActive ? 'is-active' : ''}`}>
                  <Icon size={18} aria-hidden="true" />
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <div className="sidebar-user">
          <p className="sidebar-name">{user?.name}</p>
          <p className="sidebar-email">{user?.email}</p>
          <button className="btn btn-ghost btn-sm" onClick={onLogout}>
            <LogOut size={16} aria-hidden="true" /> Sign out
          </button>
        </div>
      </aside>
      {open && <div className="scrim" onClick={() => setOpen(false)} aria-hidden="true" />}
      <div className="main-col">
        <DisclaimerBanner />
        <main id="main" className="main" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
