import { STATUS_TEXT } from '../utils/format'

export default function StatusBadge({ status }) {
  if (!status) return null
  return <span className={`badge badge-${status}`}>{STATUS_TEXT[status] || status}</span>
}

export function RiskBadge({ category }) {
  if (!category) return <span className="badge badge-neutral">No band</span>
  return <span className={`badge risk-badge risk-${category.toLowerCase()}`}>{category.charAt(0) + category.slice(1).toLowerCase()}</span>
}
