import { ErrorState, PageHeader, Spinner } from '../components/common'
import StatusBadge from '../components/StatusBadge'
import { useModels } from '../context/ModelsContext'
import { DISEASE_META, DISEASE_ORDER, formatDate, formatMetric } from '../utils/format'

export default function ModelsPage() {
  const { modules, riskBands, loading, error, reload } = useModels()
  if (loading) return <Spinner />
  if (error) return <ErrorState message={error} onRetry={reload} />

  return (
    <div className="page">
      <PageHeader title="Model performance">
        Figures below come from each model's held-out test set — patients it never saw during training or model
        selection. Small test sets mean wide uncertainty, shown as the 95% interval for ROC-AUC. None of this is
        clinical validation.
      </PageHeader>

      <div className="table-wrap panel">
        <table className="table metrics-table">
          <caption className="sr-only">Held-out evaluation metrics by module</caption>
          <thead>
            <tr>
              <th scope="col">Module</th>
              <th scope="col">Status</th>
              <th scope="col">Algorithm</th>
              <th scope="col" className="num">Test n</th>
              <th scope="col" className="num">ROC-AUC (95% CI)</th>
              <th scope="col" className="num">Accuracy</th>
              <th scope="col" className="num">Baseline acc.</th>
              <th scope="col" className="num">Sensitivity</th>
              <th scope="col" className="num">Specificity</th>
              <th scope="col" className="num">F1</th>
              <th scope="col" className="num">Brier</th>
              <th scope="col" className="num">ECE</th>
            </tr>
          </thead>
          <tbody>
            {DISEASE_ORDER.map((k) => {
              const m = modules.find((x) => x.key === k)
              const t = m?.metrics
              return (
                <tr key={k}>
                  <th scope="row">{m?.name}</th>
                  <td><StatusBadge status={m?.status} /></td>
                  <td>{m?.algorithm || '—'}</td>
                  <td className="num">{t?.n ?? '—'}</td>
                  <td className="num">{t ? `${formatMetric(t.roc_auc)} (${formatMetric(t.roc_auc_95ci[0], 2)}–${formatMetric(t.roc_auc_95ci[1], 2)})` : '—'}</td>
                  <td className="num">{formatMetric(t?.accuracy)}</td>
                  <td className="num">{formatMetric(t?.majority_baseline_accuracy)}</td>
                  <td className="num">{formatMetric(t?.recall)}</td>
                  <td className="num">{formatMetric(t?.specificity)}</td>
                  <td className="num">{formatMetric(t?.f1)}</td>
                  <td className="num">{formatMetric(t?.brier)}</td>
                  <td className="num">{formatMetric(t?.ece)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="muted small">
        Baseline accuracy is what you would score by always predicting the most common class; accuracy should be read
        against it. Brier score and ECE (expected calibration error) measure how well probabilities match observed rates —
        lower is better.
      </p>

      <div className="model-notes">
        {DISEASE_ORDER.map((k) => {
          const m = modules.find((x) => x.key === k)
          if (!m) return null
          const Icon = DISEASE_META[k].icon
          return (
            <section key={k} className={`panel model-note tone-${k}`}>
              <h2 className="panel-title"><Icon size={18} aria-hidden="true" /> {m.name}</h2>
              <p className="small">{m.dataset}. Trained {formatDate(m.trained_at, false)}.</p>
              <p className="small"><strong>Probability output:</strong> {m.probability_supported ? 'shown' : 'withheld'}. {m.probability_reason}</p>
              {m.status_reasons?.length > 0 && (
                <ul className="small reasons">{m.status_reasons.map((r) => <li key={r}>{r}</li>)}</ul>
              )}
              {m.data_caveats?.length > 0 && (
                <>
                  <p className="small"><strong>Data caveats</strong> (found by the training-data integrity checks):</p>
                  <ul className="small caveats">{m.data_caveats.map((r) => <li key={r}>{r}</li>)}</ul>
                </>
              )}
            </section>
          )
        })}
      </div>

      <section className="panel">
        <h2 className="panel-title">Risk bands</h2>
        <p className="small">
          Applied only to calibrated probabilities. Defined by this application for teaching purposes; they are not
          clinical cut-offs.
        </p>
        <ul className="band-list">
          {riskBands.map((b) => (
            <li key={b.category}><span className={`badge risk-badge risk-${b.category.toLowerCase()}`}>{b.category.charAt(0) + b.category.slice(1).toLowerCase()}</span> {b.range}</li>
          ))}
        </ul>
      </section>
    </div>
  )
}
