import { useEffect, useState } from 'react'
import { FileText } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import RiskResult from '../components/RiskResult'
import { ErrorState, PageHeader, Spinner } from '../components/common'
import { useModels } from '../context/ModelsContext'
import { adminApi, apiError } from '../services/api'
import { resultFromPrediction } from '../utils/format'

/** Admin view of any patient's single assessment: patient, result and the values used. */
export default function AdminAssessment() {
  const { id } = useParams()
  const { getModule, riskBands, loading } = useModels()
  const [pred, setPred] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    adminApi.prediction(id).then(setPred).catch((e) => setError(apiError(e).message))
  }, [id])

  if (error) return <ErrorState message={error} />
  if (!pred || loading) return <Spinner />
  const module = getModule(pred.disease)
  const result = resultFromPrediction(pred, module, riskBands)

  return (
    <div className="page page-narrow">
      <PageHeader title="Patient assessment" back={{ to: `/admin/assessments?user=${pred.patient.id}`, label: `${pred.patient.name}'s history` }} />

      <section className="panel patient-strip">
        <div>
          <p className="figure-label">Patient</p>
          <p className="patient-name">{pred.patient.name}</p>
          <p className="muted small">{pred.patient.email}</p>
        </div>
        <div>
          <p className="figure-label">Input source</p>
          <p>{pred.source === 'ocr' ? 'Lab report (OCR), reviewed by patient' : 'Entered manually'}</p>
        </div>
        <Link className="btn btn-secondary btn-sm" to={`/admin/assessments?user=${pred.patient.id}`}>
          All assessments for this patient
        </Link>
      </section>

      <RiskResult result={result} />

      <section className="panel">
        <h2 className="panel-title">Values used</h2>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th scope="col">Measurement</th><th scope="col">Value</th></tr>
            </thead>
            <tbody>
              {(module?.features || []).map((f) => {
                const v = pred.input_data?.[f.name]
                const shown = v === null || v === undefined
                  ? 'Not provided (training median substituted)'
                  : f.type === 'select'
                    ? f.options.find((o) => Number(o.value) === Number(v))?.label ?? v
                    : `${v}${f.unit ? ` ${f.unit}` : ''}`
                return (
                  <tr key={f.name}>
                    <td>{f.label}</td>
                    <td className={v === null || v === undefined ? 'muted' : ''}>{shown}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      <div className="form-actions">
        <Link className="btn btn-primary" to={`/admin/reports/${pred.id}`}>
          <FileText size={18} aria-hidden="true" /> Open printable report
        </Link>
      </div>
    </div>
  )
}
