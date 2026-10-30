import { Info, TriangleAlert } from 'lucide-react'
import { DISEASE_META, formatDate, formatPercent, RISK_TEXT } from '../utils/format'
import StatusBadge from './StatusBadge'

export const DISCLAIMER =
  'Health-Link is an educational prototype only. Its predictions are not clinically validated and must not be used for diagnosis, treatment decisions, or emergencies. Consult a qualified healthcare professional for medical concerns.'

/**
 * Reference-range strip: the 0–100% probability scale split into the
 * application's risk bands, with a marker where this estimate falls —
 * modelled on how lab reports show a value against its reference range.
 */
export function RiskGauge({ probability, bands, category }) {
  const pct = Math.min(100, Math.max(0, probability * 100))
  return (
    <figure className="gauge" aria-label={`Model probability ${formatPercent(probability)}, ${RISK_TEXT[category]} band`}>
      <div className="gauge-track">
        {bands.map((b) => (
          <div
            key={b.category}
            className={`gauge-band band-${b.category.toLowerCase()} ${b.category === category ? 'is-current' : ''}`}
            style={{ width: `${(b.max - b.min) * 100}%` }}
          >
            <span>{RISK_TEXT[b.category]}</span>
          </div>
        ))}
        <div className="gauge-marker" style={{ left: `${pct}%` }}>
          <span className={`gauge-marker-label ${pct > 88 ? 'edge-right' : pct < 12 ? 'edge-left' : ''}`}>{formatPercent(probability)}</span>
        </div>
      </div>
      <div className="gauge-scale" aria-hidden="true">
        <span>0%</span>
        {bands.slice(0, -1).map((b) => (
          <span key={b.category} style={{ left: `${b.max * 100}%` }}>
            {Math.round(b.max * 100)}%
          </span>
        ))}
        <span>100%</span>
      </div>
    </figure>
  )
}

/** The single result layout shared by every disease module. */
export default function RiskResult({ result, compact = false }) {
  const Icon = DISEASE_META[result.disease]?.icon
  const hasProb = result.probability !== null && result.probability !== undefined
  const tone = hasProb ? result.risk_category.toLowerCase() : 'none'

  return (
    <article className={`result tone-${tone}`} aria-labelledby={`result-title-${result.id || 'new'}`}>
      <header className="result-head">
        <div className="result-title">
          {Icon && <Icon size={22} aria-hidden="true" />}
          <h2 id={`result-title-${result.id || 'new'}`}>{result.disease_name} assessment</h2>
        </div>
        <div className="result-meta">
          <StatusBadge status={result.model_status} />
          {result.created_at && <time dateTime={result.created_at}>{formatDate(result.created_at)}</time>}
        </div>
      </header>

      {result.experimental_notice && (
        <div className="notice notice-warn" role="note">
          <TriangleAlert size={18} aria-hidden="true" />
          <p>{result.experimental_notice}</p>
        </div>
      )}

      <div className="result-body">
        {hasProb ? (
          <>
            <div className="result-figures">
              <div>
                <p className="figure-label">Risk category</p>
                <p className={`risk-word risk-${tone}`}>{RISK_TEXT[result.risk_category]}</p>
              </div>
              <div>
                <p className="figure-label">Estimated model probability</p>
                <p className="figure-value">{formatPercent(result.probability)}</p>
              </div>
              <div>
                <p className="figure-label">Model prediction</p>
                <p className="figure-text">{result.predicted_class ? 'Positive' : 'Negative'}</p>
                <p className="figure-sub">{result.predicted_label}</p>
              </div>
            </div>
            {result.risk_bands && (
              <RiskGauge probability={result.probability} bands={result.risk_bands} category={result.risk_category} />
            )}
          </>
        ) : (
          <div className="result-figures">
            <div>
              <p className="figure-label">Model prediction</p>
              <p className="figure-text">{result.predicted_class ? 'Positive' : 'Negative'}</p>
              <p className="figure-sub">{result.predicted_label}</p>
            </div>
            <div className="result-noprob">
              <p className="figure-label">Probability and risk category</p>
              <p className="figure-sub">Not available for this module</p>
            </div>
          </div>
        )}

        <p className="result-explanation">{result.explanation}</p>
        {!hasProb && result.risk_unavailable_reason && !result.experimental_notice && (
          <p className="muted small">Why: {result.risk_unavailable_reason}</p>
        )}

        {result.imputation_notice && (
          <div className="notice notice-info" role="note">
            <Info size={18} aria-hidden="true" />
            <p>{result.imputation_notice}</p>
          </div>
        )}

        {!compact && result.factors?.length > 0 && (
          <section className="factors" aria-label="Inputs that most influenced the model">
            <h3>What moved this estimate</h3>
            <p className="muted small">
              Inputs with the largest effect in this linear model, relative to an average patient in its training data.
              These are statistical associations, not causes.
            </p>
            <ul>
              {result.factors.map((f) => (
                <li key={f.feature}>
                  <span className={`factor-dir dir-${f.direction}`}>{f.direction === 'increases' ? 'Raised' : 'Lowered'}</span>
                  <span>{f.label}</span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>

      <footer className="result-disclaimer">
        <p>
          This result is an educational machine-learning estimate, not a clinical diagnosis. {DISCLAIMER}
        </p>
      </footer>
    </article>
  )
}
