import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { EmptyState, ErrorState, Spinner } from '../components/common'
import StatusBadge, { RiskBadge } from '../components/StatusBadge'
import { useAuth } from '../context/AuthContext'
import { useModels } from '../context/ModelsContext'
import { apiError, predictionApi } from '../services/api'
import { DISEASE_META, DISEASE_NAMES, DISEASE_ORDER, formatDate, formatPercent } from '../utils/format'

const RISK_COLORS = { LOW: 'var(--low)', MODERATE: 'var(--moderate)', HIGH: 'var(--high)', NONE: 'var(--none)' }

export default function Dashboard() {
  const { user } = useAuth()
  const { modules, loading: modelsLoading } = useModels()
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    setError('')
    predictionApi.summary().then(setSummary).catch((e) => setError(apiError(e).message))
  }, [])
  useEffect(load, [load])

  const chartData = summary
    ? DISEASE_ORDER.map((d) => ({ name: DISEASE_NAMES[d].replace('Chronic ', ''), ...summary.by_risk[d] }))
    : []

  return (
    <div className="page">
      <div className="welcome">
        <div>
          <h1>Hello, {user.name.split(' ')[0]}</h1>
          <p className="muted">
            {summary?.total
              ? `You have ${summary.total} saved assessment${summary.total === 1 ? '' : 's'}.`
              : 'Start with any module below. Results are saved to your private history.'}
          </p>
        </div>
        <div className="welcome-actions">
          <Link className="btn btn-primary" to="/assess">
            New assessment
          </Link>
          <Link className="btn btn-secondary" to="/ocr">
            Read a lab report
          </Link>
        </div>
      </div>

      <section aria-labelledby="mod-h">
        <h2 id="mod-h" className="section-title">Assessment modules</h2>
        {modelsLoading ? (
          <Spinner />
        ) : (
          <div className="module-grid">
            {DISEASE_ORDER.map((key) => {
              const m = modules.find((x) => x.key === key)
              const Icon = DISEASE_META[key].icon
              const count = summary?.by_disease?.[key] ?? 0
              const usable = m && m.status !== 'unavailable'
              return (
                <div key={key} className={`module-card tone-${key}`}>
                  <div className="module-card-top">
                    <span className="module-icon">
                      <Icon size={22} aria-hidden="true" />
                    </span>
                    <StatusBadge status={m?.status || 'unavailable'} />
                  </div>
                  <h3>{m?.name || DISEASE_NAMES[key]}</h3>
                  <p className="muted small">{DISEASE_META[key].blurb}</p>
                  <p className="small">{m?.probability_supported ? 'Shows probability and risk band' : 'Shows predicted class only'}</p>
                  <p className="small muted">{count === 0 ? 'None saved yet' : `${count} saved`}</p>
                  {usable ? (
                    <Link className="btn btn-secondary btn-sm" to={`/assess/${key}`}>
                      Start {m.short.toLowerCase()} assessment
                    </Link>
                  ) : (
                    <p className="muted small">Not available: {m?.status_reasons?.[0] || 'model not loaded'}</p>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </section>

      {error && <ErrorState message={error} onRetry={load} />}
      {!summary && !error && <Spinner />}

      {summary && (
        <div className="dash-split">
          <section className="panel" aria-labelledby="chart-h">
            <h2 id="chart-h" className="panel-title">Your assessments by module and risk band</h2>
            {summary.total ? (
              <div className="chart" role="img" aria-label="Bar chart of saved assessments per module, split by risk band">
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={chartData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="var(--line)" />
                    <XAxis dataKey="name" tick={{ fontSize: 12, fill: 'var(--ink-2)' }} tickLine={false} axisLine={false} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: 'var(--ink-2)' }} tickLine={false} axisLine={false} />
                    <Tooltip cursor={{ fill: 'var(--wash)' }} />
                    <Legend wrapperStyle={{ fontSize: 12 }} itemSorter={null} />
                    <Bar dataKey="LOW" name="Low" stackId="r" fill={RISK_COLORS.LOW} />
                    <Bar dataKey="MODERATE" name="Moderate" stackId="r" fill={RISK_COLORS.MODERATE} />
                    <Bar dataKey="HIGH" name="High" stackId="r" fill={RISK_COLORS.HIGH} />
                    <Bar dataKey="NONE" name="No band (class only)" stackId="r" fill={RISK_COLORS.NONE} radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyState title="No assessments yet">Your chart appears after your first saved assessment.</EmptyState>
            )}
          </section>

          <section className="panel" aria-labelledby="recent-h">
            <div className="panel-head">
              <h2 id="recent-h" className="panel-title">Recent assessments</h2>
              {summary.total > 0 && <Link to="/history">View all</Link>}
            </div>
            {summary.recent.length ? (
              <ul className="recent-list">
                {summary.recent.map((p) => (
                  <li key={p.id}>
                    <Link to={`/results/${p.id}`}>
                      <span className="recent-name">{DISEASE_NAMES[p.disease]}</span>
                      <span className="muted small">{formatDate(p.created_at)}</span>
                    </Link>
                    <span className="recent-right">
                      {p.probability !== null && <span className="num">{formatPercent(p.probability)}</span>}
                      <RiskBadge category={p.risk_category} />
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState title="Nothing here yet" action={<Link className="btn btn-primary btn-sm" to="/assess">Run your first assessment</Link>} />
            )}
          </section>
        </div>
      )}
    </div>
  )
}
