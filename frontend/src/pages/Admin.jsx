import { useCallback, useEffect, useState } from 'react'
import { FileText, Search } from 'lucide-react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { EmptyState, ErrorState, PageHeader, Pagination, Spinner } from '../components/common'
import StatusBadge, { RiskBadge } from '../components/StatusBadge'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { adminApi, apiError } from '../services/api'
import { DISEASE_NAMES, DISEASE_ORDER, formatDate, formatPercent } from '../utils/format'

export function AdminOverview() {
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [recent, setRecent] = useState(null)
  const [highRisk, setHighRisk] = useState([])
  const [error, setError] = useState('')
  const load = useCallback(() => {
    setError('')
    Promise.all([adminApi.stats(), adminApi.predictions({ per_page: 6 }), adminApi.analytics()])
      .then(([s, r, a]) => { setStats(s); setRecent(r.items); setHighRisk(a.high_risk_patients) })
      .catch((e) => setError(apiError(e).message))
  }, [])
  useEffect(load, [load])
  if (error) return <ErrorState message={error} onRetry={load} />
  if (!stats || !recent) return <Spinner />
  const chart = DISEASE_ORDER.map((d) => ({ name: DISEASE_NAMES[d].replace('Chronic ', ''), count: stats.predictions.by_disease[d] }))
  const patients = stats.users.total - stats.users.admins
  return (
    <div className="page">
      <div className="welcome">
        <div>
          <h1>Hello, {user.name.split(' ')[0]}</h1>
          <p className="muted">Overview of all patients and their assessments.</p>
        </div>
        <div className="welcome-actions">
          <Link className="btn btn-primary" to="/admin/assessments">Patient reports</Link>
          <Link className="btn btn-secondary" to="/admin/analysis">Disease analysis</Link>
        </div>
      </div>
      <div className="stat-row">
        <div className="stat"><p className="stat-value">{patients}</p><p className="stat-label">Registered patients</p></div>
        <div className="stat"><p className="stat-value">{stats.predictions.total}</p><p className="stat-label">Assessments run</p></div>
        <div className="stat"><p className="stat-value">{stats.predictions.by_risk.HIGH}</p><p className="stat-label">In the high band</p></div>
        <div className="stat"><p className="stat-value">{stats.predictions.by_risk.MODERATE}</p><p className="stat-label">In the moderate band</p></div>
      </div>
      <div className="dash-split">
        <section className="panel">
          <h2 className="panel-title">Assessments by module</h2>
          <div className="chart">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chart} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke="var(--line)" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                <Tooltip cursor={{ fill: 'var(--wash)' }} />
                <Bar dataKey="count" name="Assessments" fill="var(--teal)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
        <section className="panel">
          <h2 className="panel-title">Model availability</h2>
          <ul className="recent-list">
            {stats.models.map((m) => (
              <li key={m.key}>
                <span><span className="recent-name">{m.name}</span><span className="muted small">{m.algorithm || m.status_reasons[0]}</span></span>
                <StatusBadge status={m.status} />
              </li>
            ))}
          </ul>
        </section>
      </div>
      <div className="dash-split">
        <section className="panel">
          <div className="panel-head">
            <h2 className="panel-title">Latest patient assessments</h2>
            <Link to="/admin/assessments">View all</Link>
          </div>
          {recent.length ? (
            <ul className="recent-list">
              {recent.map((p) => (
                <li key={p.id}>
                  <Link to={`/admin/assessments/${p.id}`}>
                    <span className="recent-name">{p.patient.name} · {DISEASE_NAMES[p.disease]}</span>
                    <span className="muted small">{formatDate(p.created_at)}</span>
                  </Link>
                  <span className="recent-right">
                    {p.probability !== null && <span className="num">{formatPercent(p.probability)}</span>}
                    <RiskBadge category={p.risk_category} />
                  </span>
                </li>
              ))}
            </ul>
          ) : <EmptyState title="No patient assessments yet">They appear here as soon as a patient runs one.</EmptyState>}
        </section>
        <section className="panel">
          <h2 className="panel-title">Patients with high-risk results</h2>
          {highRisk.length ? (
            <ul className="recent-list">
              {highRisk.map((h) => (
                <li key={h.id}>
                  <Link to={`/admin/assessments?user=${h.id}`}>
                    <span className="recent-name">{h.name}</span>
                    <span className="muted small">{h.email}</span>
                  </Link>
                  <span className="recent-right"><RiskBadge category="HIGH" /> × {h.high_count}</span>
                </li>
              ))}
            </ul>
          ) : <p className="muted">No high-band results so far.</p>}
        </section>
      </div>
    </div>
  )
}

export function AdminPatients() {
  const navigate = useNavigate()
  const onViewHistory = (u) => navigate(`/admin/assessments?user=${u.id}`)
  const { user } = useAuth()
  const toast = useToast()
  const [users, setUsers] = useState(null)
  const [error, setError] = useState('')
  const [q, setQ] = useState('')
  const load = useCallback(() => {
    setError('')
    adminApi.users().then((d) => setUsers(d.items)).catch((e) => setError(apiError(e).message))
  }, [])
  useEffect(load, [load])

  const update = async (u, body, msg) => {
    try {
      await adminApi.updateUser(u.id, body)
      toast.success(msg)
      load()
    } catch (e) {
      toast.error(apiError(e).message)
    }
  }

  if (error) return <ErrorState message={error} onRetry={load} />
  if (!users) return <Spinner />
  const term = q.trim().toLowerCase()
  const shown = users.filter((u) => !term || u.name.toLowerCase().includes(term) || u.email.toLowerCase().includes(term))

  return (
    <div className="page">
    <PageHeader title="Patients">All registered accounts. Open a patient's history to see every assessment and report.</PageHeader>
    <section className="panel">
      <div className="panel-head">
        <h2 className="panel-title">{shown.filter((u) => u.role !== 'admin').length} patients</h2>
        <label className="search">
          <Search size={16} aria-hidden="true" />
          <span className="sr-only">Search patients</span>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name or email" />
        </label>
      </div>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr><th scope="col">Name</th><th scope="col">Email</th><th scope="col">Role</th><th scope="col">Joined</th>
              <th scope="col" className="num">Assessments</th><th scope="col">Status</th><th scope="col"><span className="sr-only">Actions</span></th></tr>
          </thead>
          <tbody>
            {shown.map((u) => (
              <tr key={u.id}>
                <td>{u.name}</td>
                <td>{u.email}</td>
                <td>{u.role === 'admin' ? 'Administrator' : 'Patient'}</td>
                <td>{formatDate(u.created_at, false)}</td>
                <td className="num">{u.prediction_count}</td>
                <td>{u.is_active ? 'Active' : 'Deactivated'}</td>
                <td className="actions">
                  {u.role !== 'admin' && (
                    <button className="btn btn-secondary btn-sm" onClick={() => onViewHistory(u)} disabled={!u.prediction_count}>
                      View history
                    </button>
                  )}
                  {u.id !== user.id && (
                    <>
                      <button className="btn btn-ghost btn-sm" onClick={() => update(u, { is_active: !u.is_active }, u.is_active ? 'Account deactivated.' : 'Account reactivated.')}>
                        {u.is_active ? 'Deactivate' : 'Reactivate'}
                      </button>
                      <button className="btn btn-ghost btn-sm" onClick={() => update(u, { role: u.role === 'admin' ? 'user' : 'admin' }, 'Role updated.')}>
                        {u.role === 'admin' ? 'Make patient' : 'Make admin'}
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!shown.length && <p className="muted">No accounts match “{q}”.</p>}
    </section>
    </div>
  )
}

export function AdminAssessments() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const userId = params.get('user') || ''
  const onClearUser = () => setParams({})
  const [filters, setFilters] = useState({ disease: params.get('disease') || '', risk: '', q: '' })
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [patient, setPatient] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => setPage(1), [userId, filters.disease, filters.risk, query])

  useEffect(() => {
    if (!userId) return setPatient(null)
    adminApi.user(userId).then(setPatient).catch(() => setPatient(null))
  }, [userId])

  const load = useCallback(() => {
    setError('')
    const params = { page, per_page: 15 }
    if (userId) params.user_id = userId
    if (filters.disease) params.disease = filters.disease
    if (filters.risk) params.risk = filters.risk
    if (query) params.q = query
    adminApi.predictions(params).then(setData).catch((e) => setError(apiError(e).message))
  }, [page, userId, filters.disease, filters.risk, query])
  useEffect(load, [load])

  return (
    <div className="page">
      <PageHeader title={patient ? `${patient.user.name}'s history` : 'Patient reports'}>
        {patient ? 'Every assessment this patient has run.' : "Every patient's assessments. Open one to see the values used and its printable report."}
      </PageHeader>
      {patient && (
        <section className="panel patient-strip">
          <div>
            <p className="figure-label">Patient history</p>
            <p className="patient-name">{patient.user.name}</p>
            <p className="muted small">{patient.user.email} · joined {formatDate(patient.user.created_at, false)}</p>
          </div>
          <div className="patient-counts">
            {DISEASE_ORDER.map((d) => (
              <span key={d} className="small"><strong>{patient.by_disease[d]}</strong> {DISEASE_NAMES[d].replace('Chronic ', '')}</span>
            ))}
          </div>
          <div className="patient-counts">
            <RiskBadge category="HIGH" /> {patient.by_risk.HIGH}
            <RiskBadge category="MODERATE" /> {patient.by_risk.MODERATE}
            <RiskBadge category="LOW" /> {patient.by_risk.LOW}
          </div>
          <button className="btn btn-ghost btn-sm" onClick={onClearUser}>Show all patients</button>
        </section>
      )}

      <form className="toolbar wrap" onSubmit={(e) => { e.preventDefault(); setQuery(filters.q.trim()) }}>
        {!userId && (
          <label className="search">
            <Search size={16} aria-hidden="true" />
            <span className="sr-only">Search by patient</span>
            <input value={filters.q} onChange={(e) => setFilters({ ...filters, q: e.target.value })} onBlur={() => setQuery(filters.q.trim())}
              placeholder="Patient name or email" />
          </label>
        )}
        <label className="sr-only" htmlFor="f-dis">Module</label>
        <select id="f-dis" value={filters.disease} onChange={(e) => setFilters({ ...filters, disease: e.target.value })}>
          <option value="">All modules</option>
          {DISEASE_ORDER.map((d) => <option key={d} value={d}>{DISEASE_NAMES[d]}</option>)}
        </select>
        <label className="sr-only" htmlFor="f-risk">Risk band</label>
        <select id="f-risk" value={filters.risk} onChange={(e) => setFilters({ ...filters, risk: e.target.value })}>
          <option value="">All risk bands</option>
          <option value="HIGH">High</option>
          <option value="MODERATE">Moderate</option>
          <option value="LOW">Low</option>
          <option value="NONE">No band</option>
        </select>
      </form>

      {error && <ErrorState message={error} onRetry={load} />}
      {!data && !error && <Spinner />}
      {data && data.items.length === 0 && <EmptyState title="No assessments match these filters" />}
      {data && data.items.length > 0 && (
        <section className="panel">
          <div className="table-wrap">
            <table className="table">
              <caption className="sr-only">Patient assessments</caption>
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  {!userId && <th scope="col">Patient</th>}
                  <th scope="col">Module</th>
                  <th scope="col">Prediction</th>
                  <th scope="col" className="num">Probability</th>
                  <th scope="col">Risk</th>
                  <th scope="col"><span className="sr-only">Report</span></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((p) => (
                  <tr key={p.id} className="row-link" onClick={() => navigate(`/admin/assessments/${p.id}`)}>
                    <td>{formatDate(p.created_at)}</td>
                    {!userId && (
                      <td>
                        <span className="recent-name">{p.patient.name}</span>
                        <br />
                        <span className="muted small">{p.patient.email}</span>
                      </td>
                    )}
                    <td>
                      <Link to={`/admin/assessments/${p.id}`} onClick={(e) => e.stopPropagation()}>{DISEASE_NAMES[p.disease]}</Link>
                      {p.source === 'ocr' && <span className="muted small"> (from report)</span>}
                    </td>
                    <td>{p.predicted_class ? 'Positive' : 'Negative'}</td>
                    <td className="num">{formatPercent(p.probability)}</td>
                    <td><RiskBadge category={p.risk_category} /></td>
                    <td className="actions">
                      <Link className="icon-btn" to={`/admin/reports/${p.id}`} aria-label="Open report" onClick={(e) => e.stopPropagation()}>
                        <FileText size={17} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted small">{data.total} assessment{data.total === 1 ? '' : 's'}</p>
          <Pagination page={data.page} pages={data.pages} onChange={setPage} />
        </section>
      )}
    </div>
  )
}
