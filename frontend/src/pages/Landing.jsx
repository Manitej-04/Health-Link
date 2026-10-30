import { Link, Navigate } from 'react-router-dom'
import { RiskGauge } from '../components/RiskResult'
import { DisclaimerBanner, homeFor, Spinner } from '../components/common'
import Logo from '../components/Logo'
import StatusBadge from '../components/StatusBadge'
import { useAuth } from '../context/AuthContext'
import { useModels } from '../context/ModelsContext'
import { DISEASE_META, DISEASE_ORDER } from '../utils/format'

const DEMO_BANDS = [
  { category: 'LOW', min: 0, max: 0.3 },
  { category: 'MODERATE', min: 0.3, max: 0.7 },
  { category: 'HIGH', min: 0.7, max: 1 },
]

export default function Landing() {
  const { user, loading } = useAuth()
  const { modules, riskBands } = useModels()
  if (loading) return <Spinner />
  if (user) return <Navigate to={homeFor(user)} replace />

  return (
    <div className="landing">
      <DisclaimerBanner />
      <header className="landing-nav">
        <Logo to="/" />
        <nav>
          <Link className="btn btn-ghost" to="/login">
            Sign in
          </Link>
          <Link className="btn btn-primary" to="/register">
            Create account
          </Link>
        </nav>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <h1>See where a set of lab values sits on a model's risk scale.</h1>
          <p className="lede">
            Health-Link runs machine-learning models trained on four public clinical datasets — heart disease, diabetes,
            chronic kidney disease and liver disease — and shows you the result the way a lab report shows a reading
            against its reference range. It is a learning tool, not a diagnosis.
          </p>
          <div className="hero-actions">
            <Link className="btn btn-primary btn-lg" to="/register">
              Create a free account
            </Link>
            <Link className="btn btn-secondary btn-lg" to="/login">
              Sign in
            </Link>
          </div>
        </div>
        <div className="hero-sample" aria-label="Example of a result strip">
          <p className="sample-caption">How a result is shown</p>
          <p className="sample-title">Example: estimated model probability 42%</p>
          <RiskGauge probability={0.42} bands={riskBands.length ? riskBands : DEMO_BANDS} category="MODERATE" />
          <p className="muted small">
            Bands are application-defined for teaching: below 30% low, 30–70% moderate, 70% and above high. They are
            not clinical thresholds.
          </p>
        </div>
      </section>

      <section className="landing-modules" aria-labelledby="modules-heading">
        <h2 id="modules-heading">Four modules, each evaluated before it is offered</h2>
        <p className="muted">
          Every model is evaluated on held-out patients, and its probabilities are checked for calibration. Known
          limitations of each dataset are listed on the Model performance page.
        </p>
        <ul className="module-list">
          {DISEASE_ORDER.map((key) => {
            const m = modules.find((x) => x.key === key)
            const Icon = DISEASE_META[key].icon
            return (
              <li key={key} className={`module-row tone-${key}`}>
                <Icon size={22} aria-hidden="true" />
                <div>
                  <p className="module-name">{m?.name || key}</p>
                  <p className="muted small">{m?.dataset || DISEASE_META[key].blurb}</p>
                </div>
                {m && <StatusBadge status={m.status} />}
              </li>
            )
          })}
        </ul>
      </section>

      <section className="landing-steps" aria-labelledby="how-heading">
        <h2 id="how-heading">How it works</h2>
        <ol>
          <li>
            <strong>Enter your values</strong> on a form built from the model's own input list, or read them from a
            photo or PDF of a lab report and check each one.
          </li>
          <li>
            <strong>The server validates and runs the model</strong>, then applies probability calibration checked on
            patients the model never saw.
          </li>
          <li>
            <strong>Review and print</strong> the result, kept in your private history.
          </li>
        </ol>
      </section>

      <footer className="landing-footer">
        <p className="muted small">Health-Link — final-year engineering project. Educational use only.</p>
      </footer>
    </div>
  )
}
