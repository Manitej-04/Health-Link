import { useCallback, useEffect, useState } from 'react'
import { FileText, Trash2 } from 'lucide-react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import RiskResult from '../components/RiskResult'
import { EmptyState, ErrorState, PageHeader, Pagination, Spinner } from '../components/common'
import { RiskBadge } from '../components/StatusBadge'
import { useModels } from '../context/ModelsContext'
import { useToast } from '../context/ToastContext'
import { apiError, predictionApi } from '../services/api'
import { DISEASE_NAMES, DISEASE_ORDER, formatDate, formatPercent, resultFromPrediction } from '../utils/format'

export function ResultPage() {
  const { id } = useParams()
  const location = useLocation()
  const { getModule, riskBands, loading: modelsLoading } = useModels()
  const fresh = location.state?.result?.id === Number(id) ? location.state.result : null
  const [result, setResult] = useState(fresh)
  const [error, setError] = useState('')

  useEffect(() => {
    if (fresh || modelsLoading) return
    setError('')
    predictionApi
      .get(id)
      .then((p) => setResult(resultFromPrediction(p, getModule(p.disease), riskBands)))
      .catch((e) => setError(apiError(e).message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, fresh, modelsLoading])

  if (error) return <ErrorState message={error} />
  if (!result) return <Spinner />
  return (
    <div className="page page-narrow">
      <PageHeader title="Assessment result" back={{ to: '/history', label: 'History' }} />
      <RiskResult result={result} />
      <div className="form-actions">
        <Link className="btn btn-primary" to={`/reports/${result.id}`}>
          <FileText size={18} aria-hidden="true" /> Open printable report
        </Link>
        <Link className="btn btn-secondary" to={`/assess/${result.disease}`}>
          New {DISEASE_NAMES[result.disease].toLowerCase()} assessment
        </Link>
      </div>
    </div>
  )
}

export function HistoryPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [disease, setDisease] = useState('')
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    setError('')
    predictionApi
      .history({ page, per_page: 10, ...(disease ? { disease } : {}) })
      .then(setData)
      .catch((e) => setError(apiError(e).message))
  }, [page, disease])
  useEffect(load, [load])

  const remove = async (id) => {
    if (!window.confirm('Delete this assessment from your history? This cannot be undone.')) return
    try {
      await predictionApi.remove(id)
      toast.success('Assessment deleted.')
      if (data.items.length === 1 && page > 1) setPage(page - 1)
      else load()
    } catch (e) {
      toast.error(apiError(e).message)
    }
  }

  return (
    <div className="page">
      <PageHeader title="Assessment history">Only you can see these records.</PageHeader>
      <div className="toolbar">
        <label htmlFor="filter">Module</label>
        <select id="filter" value={disease} onChange={(e) => { setDisease(e.target.value); setPage(1) }}>
          <option value="">All modules</option>
          {DISEASE_ORDER.map((d) => (
            <option key={d} value={d}>
              {DISEASE_NAMES[d]}
            </option>
          ))}
        </select>
      </div>
      {error && <ErrorState message={error} onRetry={load} />}
      {!data && !error && <Spinner />}
      {data && data.items.length === 0 && (
        <EmptyState title={disease ? 'No assessments for this module yet' : 'No assessments yet'}
          action={<Link className="btn btn-primary btn-sm" to="/assess">Start an assessment</Link>} />
      )}
      {data && data.items.length > 0 && (
        <>
          <div className="table-wrap">
            <table className="table">
              <caption className="sr-only">Your saved assessments</caption>
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  <th scope="col">Module</th>
                  <th scope="col">Prediction</th>
                  <th scope="col" className="num">Probability</th>
                  <th scope="col">Risk</th>
                  <th scope="col"><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((p) => (
                  <tr key={p.id} className="row-link" onClick={() => navigate(`/results/${p.id}`)}>
                    <td>{formatDate(p.created_at)}</td>
                    <td>
                      <Link to={`/results/${p.id}`} onClick={(e) => e.stopPropagation()}>{DISEASE_NAMES[p.disease]}</Link>
                      {p.source === 'ocr' && <span className="muted small"> (from report)</span>}
                    </td>
                    <td>{p.predicted_class ? 'Positive' : 'Negative'}</td>
                    <td className="num">{formatPercent(p.probability)}</td>
                    <td><RiskBadge category={p.risk_category} /></td>
                    <td className="actions">
                      <Link className="icon-btn" to={`/reports/${p.id}`} aria-label="Open report" onClick={(e) => e.stopPropagation()}>
                        <FileText size={17} />
                      </Link>
                      <button className="icon-btn danger" aria-label="Delete assessment" onClick={(e) => { e.stopPropagation(); remove(p.id) }}>
                        <Trash2 size={17} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted small">{data.total} assessment{data.total === 1 ? '' : 's'}</p>
          <Pagination page={data.page} pages={data.pages} onChange={setPage} />
        </>
      )}
    </div>
  )
}
