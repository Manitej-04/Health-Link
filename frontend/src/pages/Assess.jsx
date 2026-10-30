import { useState } from 'react'
import { TriangleAlert } from 'lucide-react'
import { Link, Navigate, useLocation, useNavigate, useParams } from 'react-router-dom'
import AssessmentForm from '../components/AssessmentForm'
import { ErrorState, PageHeader, Spinner } from '../components/common'
import StatusBadge from '../components/StatusBadge'
import { useModels } from '../context/ModelsContext'
import { useToast } from '../context/ToastContext'
import { apiError, predictionApi } from '../services/api'
import { DISEASE_META, DISEASE_ORDER } from '../utils/format'

export function DiseaseSelect() {
  const { modules, loading, error, reload } = useModels()
  if (loading) return <Spinner />
  if (error) return <ErrorState message={error} onRetry={reload} />
  return (
    <div className="page">
      <PageHeader title="Choose an assessment">
        Each form asks for exactly the measurements its model was trained on. Have your recent test results to hand.
      </PageHeader>
      <ul className="select-list">
        {DISEASE_ORDER.map((key) => {
          const m = modules.find((x) => x.key === key)
          const Icon = DISEASE_META[key].icon
          const usable = m && m.status !== 'unavailable'
          const required = m?.features.filter((f) => f.required).length
          const inner = (
            <>
              <span className={`module-icon tone-${key}`}>
                <Icon size={24} aria-hidden="true" />
              </span>
              <span className="select-body">
                <span className="select-title">{m?.name}</span>
                <span className="muted small">
                  {DISEASE_META[key].blurb}. {m ? `${required} required inputs` : ''}
                  {m && m.features.length > required ? `, ${m.features.length - required} optional` : ''}.
                </span>
              </span>
              <StatusBadge status={m?.status || 'unavailable'} />
            </>
          )
          return (
            <li key={key}>
              {usable ? (
                <Link className="select-item" to={`/assess/${key}`}>
                  {inner}
                </Link>
              ) : (
                <div className="select-item is-disabled" aria-disabled="true">
                  {inner}
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export function AssessmentPage() {
  const { disease } = useParams()
  const { getModule, loading, error, reload } = useModels()
  const navigate = useNavigate()
  const location = useLocation()
  const toast = useToast()
  const [serverErrors, setServerErrors] = useState({})
  const [formError, setFormError] = useState('')

  if (!DISEASE_ORDER.includes(disease)) return <Navigate to="/assess" replace />
  if (loading) return <Spinner />
  if (error) return <ErrorState message={error} onRetry={reload} />
  const module = getModule(disease)
  const prefill = location.state?.prefill || {}
  const fromOcr = location.state?.source === 'ocr'

  const onSubmit = async (features) => {
    setServerErrors({})
    setFormError('')
    try {
      const result = await predictionApi.predict(disease, features, fromOcr ? 'ocr' : 'manual')
      toast.success('Assessment saved to your history.')
      navigate(`/results/${result.id}`, { state: { result } })
    } catch (err) {
      const e = apiError(err)
      setServerErrors(e.details || {})
      setFormError(e.message)
      toast.error(e.message)
    }
  }

  return (
    <div className="page">
      <PageHeader title={`${module.name} assessment`} back={{ to: '/assess', label: 'All assessments' }}>
        <p>
          Model: {module.algorithm} trained on {module.dataset}. <StatusBadge status={module.status} />
        </p>
        {module.population_note && <p className="muted">{module.population_note}</p>}
      </PageHeader>

      {module.status === 'unavailable' && (
        <ErrorState message={`This module is unavailable: ${module.status_reasons.join('; ')}`} />
      )}
      {module.status === 'experimental' && (
        <div className="notice notice-warn" role="note">
          <TriangleAlert size={18} aria-hidden="true" />
          <p>
            Experimental module — its training data failed integrity checks, so results show a predicted class only,
            without a probability or risk band. {module.status_reasons.join(' ')}
          </p>
        </div>
      )}
      {fromOcr && (
        <p className="notice notice-info" role="note">
          Values marked “Read from your report” came from the uploaded file. Check each one against the report and fill
          in anything missing before continuing.
        </p>
      )}

      {module.status !== 'unavailable' && (
        <div className="panel">
          {formError && (
            <p className="form-error" role="alert">
              {formError}
            </p>
          )}
          <AssessmentForm module={module} initialValues={prefill} reportFields={Object.keys(prefill)} onSubmit={onSubmit}
            serverErrors={serverErrors} />
        </div>
      )}
    </div>
  )
}
