import { ChevronLeft, ChevronRight, LoaderCircle, TriangleAlert } from 'lucide-react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { DISCLAIMER } from './RiskResult'

export function Spinner({ label = 'Loading…' }) {
  return (
    <div className="spinner" role="status">
      <LoaderCircle className="spin" size={22} aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="state-box state-error" role="alert">
      <TriangleAlert size={20} aria-hidden="true" />
      <p>{message}</p>
      {onRetry && (
        <button className="btn btn-secondary btn-sm" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="state-box state-empty">
      <p className="state-title">{title}</p>
      {children && <p className="muted">{children}</p>}
      {action}
    </div>
  )
}

export function DisclaimerBanner() {
  return (
    <div className="disclaimer-banner" role="note">
      <TriangleAlert size={16} aria-hidden="true" />
      <p>{DISCLAIMER}</p>
    </div>
  )
}

export function Pagination({ page, pages, onChange }) {
  if (pages <= 1) return null
  return (
    <nav className="pagination" aria-label="Pagination">
      <button className="btn btn-secondary btn-sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        <ChevronLeft size={16} aria-hidden="true" /> Previous
      </button>
      <span>
        Page {page} of {pages}
      </span>
      <button className="btn btn-secondary btn-sm" disabled={page >= pages} onClick={() => onChange(page + 1)}>
        Next <ChevronRight size={16} aria-hidden="true" />
      </button>
    </nav>
  )
}

/** Where each role lands after signing in. */
export const homeFor = (user) => (user?.role === 'admin' ? '/admin' : '/dashboard')

/**
 * role="admin": administrators only. role="patient": patient-only pages
 * (assessments, own history); administrators are sent to their own area.
 */
export function ProtectedRoute({ children, role }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <Spinner label="Checking your session…" />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (role === 'admin' && user.role !== 'admin') return <Navigate to="/dashboard" replace />
  if (role === 'patient' && user.role === 'admin') return <Navigate to="/admin" replace />
  return children
}

export function PageHeader({ title, children, back }) {
  return (
    <div className="page-header">
      {back && (
        <Link className="back-link" to={back.to}>
          <ChevronLeft size={16} aria-hidden="true" /> {back.label}
        </Link>
      )}
      <h1>{title}</h1>
      {children && <div className="page-intro">{children}</div>}
    </div>
  )
}
