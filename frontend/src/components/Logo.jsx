import { Link } from 'react-router-dom'

export default function Logo({ to = '/dashboard' }) {
  return (
    <Link to={to} className="logo" aria-label="Health-Link home">
      <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true">
        <rect width="32" height="32" rx="7" fill="var(--teal)" />
        <path d="M5 17h6l2.5-6 4 11 2.5-5H27" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span>Health-Link</span>
    </Link>
  )
}
