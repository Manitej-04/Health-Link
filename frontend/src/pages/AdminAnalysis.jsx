import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { EmptyState, ErrorState, PageHeader, Spinner } from '../components/common'
import { RiskBadge } from '../components/StatusBadge'
import { adminApi, apiError } from '../services/api'
import { DISEASE_META, DISEASE_NAMES, DISEASE_ORDER, formatPercent } from '../utils/format'

const SHORT = { heart: 'Heart', diabetes: 'Diabetes', kidney: 'Kidney', liver: 'Liver' }
const LINE_COLORS = { heart: 'var(--heart)', diabetes: 'var(--diabetes)', kidney: 'var(--kidney)', liver: 'var(--liver)' }

/** Disease-wise analysis across every patient's assessments. */
export default function AdminAnalysis() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const load = useCallback(() => {
    setError('')
    adminApi.analytics().then(setData).catch((e) => setError(apiError(e).message))
  }, [])
  useEffect(load, [load])

  if (error) return <ErrorState message={error} onRetry={load} />
  if (!data) return <Spinner />
  const total = DISEASE_ORDER.reduce((n, d) => n + data.diseases[d].total, 0)

  const riskChart = DISEASE_ORDER.map((d) => ({ name: SHORT[d], ...data.diseases[d].by_risk }))
  const timeline = data.timeline.map((t) => ({
    ...t,
    label: new Date(t.date + 'T00:00:00').toLocaleDateString(undefined, { day: 'numeric', month: 'short' }),
  }))

  return (
    <div className="page">
      <PageHeader title="Disease analysis">
        How each disease module is being used across all patients, and how results are distributed across the
        risk bands. Figures are counts of assessments run in Health-Link, not prevalence in any population.
      </PageHeader>

      {total === 0 ? (
        <EmptyState title="No assessments yet">Charts appear once patients start running assessments.</EmptyState>
      ) : (
        <>
          <div className="disease-grid">
            {DISEASE_ORDER.map((d) => {
              const s = data.diseases[d]
              const Icon = DISEASE_META[d].icon
              return (
                <section key={d} className={`panel disease-card tone-${d}`}>
                  <h2 className="panel-title">
                    <span className={`module-icon tone-${d}`}><Icon size={18} aria-hidden="true" /></span>
                    {DISEASE_NAMES[d]}
                  </h2>
                  <dl className="disease-stats">
                    <div><dt>Assessments</dt><dd>{s.total}</dd></div>
                    <div><dt>Patients</dt><dd>{s.patients}</dd></div>
                    <div><dt>Predicted positive</dt><dd>{s.total ? `${s.positive} (${formatPercent(s.positive_rate, 0)})` : '—'}</dd></div>
                    <div><dt>Average probability</dt><dd>{formatPercent(s.avg_probability)}</dd></div>
                  </dl>
                  <div className="band-row">
                    <RiskBadge category="HIGH" /> {s.by_risk.HIGH}
                    <RiskBadge category="MODERATE" /> {s.by_risk.MODERATE}
                    <RiskBadge category="LOW" /> {s.by_risk.LOW}
                  </div>
                  {s.total > 0 && (
                    <Link className="small" to={`/admin/assessments?disease=${d}`}>View {SHORT[d].toLowerCase()} reports</Link>
                  )}
                </section>
              )
            })}
          </div>

          <div className="dash-split">
            <section className="panel">
              <h2 className="panel-title">Risk bands by disease</h2>
              <div className="chart" role="img" aria-label="Stacked bars of assessments per disease split by risk band">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={riskChart} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="var(--line)" />
                    <XAxis dataKey="name" tick={{ fontSize: 12, fill: 'var(--ink-2)' }} tickLine={false} axisLine={false} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: 'var(--ink-2)' }} tickLine={false} axisLine={false} />
                    <Tooltip cursor={{ fill: 'var(--wash)' }} />
                    <Legend wrapperStyle={{ fontSize: 12 }} itemSorter={null} />
                    <Bar dataKey="LOW" name="Low" stackId="r" fill="var(--low)" />
                    <Bar dataKey="MODERATE" name="Moderate" stackId="r" fill="var(--moderate)" />
                    <Bar dataKey="HIGH" name="High" stackId="r" fill="var(--high)" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>
            <section className="panel">
              <h2 className="panel-title">Patients with high-risk results</h2>
              {data.high_risk_patients.length ? (
                <ul className="recent-list">
                  {data.high_risk_patients.map((h) => (
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

          <section className="panel">
            <h2 className="panel-title">Assessments per day, last 30 days</h2>
            <div className="chart" role="img" aria-label="Stacked bar chart of assessments per day for each disease over the last 30 days">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={timeline} margin={{ top: 8, right: 12, left: -18, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="var(--line)" />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: 'var(--ink-2)' }} tickLine={false} axisLine={false} interval={4} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: 'var(--ink-2)' }} tickLine={false} axisLine={false} />
                  <Tooltip cursor={{ fill: 'var(--wash)' }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} itemSorter={null} />
                  {DISEASE_ORDER.map((d) => (
                    <Bar key={d} dataKey={d} name={SHORT[d]} stackId="day" fill={LINE_COLORS[d]} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>
        </>
      )}
    </div>
  )
}
