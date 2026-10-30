import { useEffect, useState } from 'react'
import { Printer } from 'lucide-react'
import { RiskGauge } from '../components/RiskResult'
import { ErrorState, PageHeader, Spinner } from '../components/common'
import { adminApi, apiError, predictionApi } from '../services/api'
import { formatDate, formatMetric, formatPercent, RISK_TEXT } from '../utils/format'
import { useParams } from 'react-router-dom'
import Logo from '../components/Logo'

export default function ReportPage({ admin = false }) {
  const { id } = useParams()
  const [rep, setRep] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    ;(admin ? adminApi.report(id) : predictionApi.report(id)).then(setRep).catch((e) => setError(apiError(e).message))
  }, [id, admin])

  if (error) return <ErrorState message={error} />
  if (!rep) return <Spinner />
  const p = rep.prediction
  const m = rep.model.current_metrics

  return (
    <div className="page page-narrow">
      <div className="no-print">
        <PageHeader title="Printable report" back={admin ? { to: `/admin/assessments/${p.id}`, label: 'Assessment' } : { to: `/results/${p.id}`, label: 'Result' }} />
        <div className="form-actions">
          <button className="btn btn-primary" onClick={() => window.print()}>
            <Printer size={18} aria-hidden="true" /> Print or save as PDF
          </button>
        </div>
      </div>

      <article className="report">
        <header className="report-head">
          <Logo />
          <div className="report-ids">
            <p><strong>Report</strong> {rep.report_id}</p>
            <p><strong>Date</strong> {formatDate(p.created_at)}</p>
            <p><strong>Prepared for</strong> {rep.generated_for.name}</p>
            {admin && <p><strong>Email</strong> {rep.generated_for.email}</p>}
          </div>
        </header>
        <p className="report-warning">Educational machine-learning estimate — not a medical report or diagnosis.</p>

        <h2>{rep.disease_name} assessment</h2>
        <table className="report-table">
          <tbody>
            <tr><th scope="row">Model prediction</th><td>{p.predicted_class ? 'Positive' : 'Negative'} — {p.predicted_label}</td></tr>
            <tr><th scope="row">Estimated model probability</th><td>{p.probability !== null ? formatPercent(p.probability) : 'Not available for this module'}</td></tr>
            <tr><th scope="row">Risk category</th><td>{p.risk_category ? `${RISK_TEXT[p.risk_category]} (application-defined educational band)` : 'Not available for this module'}</td></tr>
            <tr><th scope="row">Module status at prediction</th><td>{p.model_status}</td></tr>
            <tr><th scope="row">Input source</th><td>{p.source === 'ocr' ? 'Lab report (OCR), reviewed by user' : 'Entered manually'}</td></tr>
          </tbody>
        </table>
        {p.probability !== null && rep.risk_bands && (
          <RiskGauge probability={p.probability} bands={rep.risk_bands} category={p.risk_category} />
        )}

        <h3>Values used</h3>
        <table className="report-table report-inputs">
          <thead><tr><th scope="col">Measurement</th><th scope="col">Value</th></tr></thead>
          <tbody>
            {rep.inputs.map((i) => (
              <tr key={i.feature}>
                <td>{i.label}</td>
                <td className={i.value === null ? 'muted' : ''}>
                  {i.display}{i.value !== null && i.unit ? ` ${i.unit}` : ''}
                  {i.value === null && ' (training median substituted)'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <h3>About the model</h3>
        <p>
          {rep.model.algorithm} with sigmoid probability calibration, trained {formatDate(rep.model.version, false)} on{' '}
          {rep.model.dataset}.
          {m && ` Held-out test set (n=${m.n}): ROC-AUC ${formatMetric(m.roc_auc)}, accuracy ${formatMetric(m.accuracy)}, sensitivity ${formatMetric(m.recall)}, specificity ${formatMetric(m.specificity)}.`}
        </p>
        <footer className="report-disclaimer">
          <p>{rep.disclaimer}</p>
        </footer>
      </article>
    </div>
  )
}
