import { useState } from 'react'
import { LoaderCircle, Upload } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/common'
import { useModels } from '../context/ModelsContext'
import { useToast } from '../context/ToastContext'
import { apiError, ocrApi } from '../services/api'
import { DISEASE_NAMES, DISEASE_ORDER } from '../utils/format'

const MAX_MB = 5
const TYPES = ['image/png', 'image/jpeg', 'application/pdf']

export default function OcrPage() {
  const { getModule } = useModels()
  const toast = useToast()
  const navigate = useNavigate()
  const [disease, setDisease] = useState('liver')
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [edits, setEdits] = useState({})
  const [excluded, setExcluded] = useState(new Set())

  const pick = (f) => {
    setError('')
    setResult(null)
    if (!f) return setFile(null)
    if (!TYPES.includes(f.type)) return setError('Choose a PNG, JPEG or PDF file.')
    if (f.size > MAX_MB * 1024 * 1024) return setError(`The file is larger than ${MAX_MB} MB.`)
    setFile(f)
  }

  const run = async (e) => {
    e.preventDefault()
    if (!file || busy) return
    setBusy(true)
    setError('')
    try {
      const r = await ocrApi.extract(disease, file)
      setResult(r)
      setEdits(Object.fromEntries(r.extracted.map((x) => [x.field, String(x.value)])))
      setExcluded(new Set(r.extracted.filter((x) => !x.valid).map((x) => x.field)))
      if (!r.extracted.length) toast.info('No labelled measurements were recognised in this file.')
    } catch (err) {
      setError(apiError(err).message)
    } finally {
      setBusy(false)
    }
  }

  const toggle = (field) =>
    setExcluded((s) => {
      const n = new Set(s)
      n.has(field) ? n.delete(field) : n.add(field)
      return n
    })

  const proceed = () => {
    const prefill = Object.fromEntries(Object.entries(edits).filter(([k, v]) => !excluded.has(k) && String(v).trim() !== ''))
    navigate(`/assess/${disease}`, { state: { prefill, source: 'ocr' } })
  }

  const module = getModule(disease)
  const fieldInfo = (name) => module?.features.find((f) => f.name === name)

  return (
    <div className="page">
      <PageHeader title="Read values from a lab report">
        Upload a clear photo, scan or PDF of a printed report. Health-Link only picks up numbers that sit next to a
        recognised label, shows you what it found, and leaves everything else for you to fill in. Nothing is run until
        you review the form. Files are processed in memory and not stored.
      </PageHeader>

      <form className="panel ocr-form" onSubmit={run}>
        <div className="field">
          <label htmlFor="ocr-disease">Which assessment is this report for?</label>
          <select id="ocr-disease" value={disease} onChange={(e) => { setDisease(e.target.value); setResult(null) }}>
            {DISEASE_ORDER.map((d) => (
              <option key={d} value={d} disabled={getModule(d)?.status === 'unavailable'}>
                {DISEASE_NAMES[d]}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="ocr-file">Report file (PNG, JPEG or PDF, up to {MAX_MB} MB)</label>
          <div className="dropzone">
            <Upload size={20} aria-hidden="true" />
            <input id="ocr-file" type="file" accept=".png,.jpg,.jpeg,.pdf,image/png,image/jpeg,application/pdf"
              onChange={(e) => pick(e.target.files?.[0])} />
          </div>
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="btn btn-primary" disabled={!file || busy}>
          {busy ? (<><LoaderCircle className="spin" size={18} aria-hidden="true" /> Reading the report…</>) : 'Extract values'}
        </button>
      </form>

      {result && (
        <section className="panel" aria-labelledby="ocr-review">
          <h2 id="ocr-review" className="panel-title">Review what was found</h2>
          {result.extracted.length > 0 ? (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th scope="col">Use</th>
                    <th scope="col">Measurement</th>
                    <th scope="col">Value</th>
                    <th scope="col">Line in report</th>
                  </tr>
                </thead>
                <tbody>
                  {result.extracted.map((x) => {
                    const f = fieldInfo(x.field)
                    const opts = f?.type === 'select' ? f.options : null
                    return (
                      <tr key={x.field} className={excluded.has(x.field) ? 'is-excluded' : ''}>
                        <td>
                          <input type="checkbox" aria-label={`Use ${x.label}`} checked={!excluded.has(x.field)} onChange={() => toggle(x.field)} />
                        </td>
                        <td>
                          {x.label}
                          {!x.valid && <p className="field-error">{x.error}</p>}
                        </td>
                        <td>
                          {opts ? (
                            <select aria-label={x.label} value={edits[x.field]} onChange={(e) => setEdits({ ...edits, [x.field]: e.target.value })}>
                              {opts.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                            </select>
                          ) : (
                            <span className="input-unit">
                              <input aria-label={x.label} type="number" step="any" value={edits[x.field]}
                                onChange={(e) => setEdits({ ...edits, [x.field]: e.target.value })} />
                              {f?.unit && <span className="unit">{f.unit}</span>}
                            </span>
                          )}
                        </td>
                        <td className="muted small source-line">{x.source_line}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted">No labelled measurements were recognised. Try a sharper image, or enter values manually.</p>
          )}
          {result.missing.length > 0 && (
            <p className="small">
              <strong>Not found — you will enter these on the form:</strong>{' '}
              {result.missing.map((m) => m.label).join(', ')}.
            </p>
          )}
          <details>
            <summary className="small">Show recognised text</summary>
            <pre className="ocr-text">{result.text_preview || '(no text recognised)'}</pre>
          </details>
          <div className="form-actions">
            <button className="btn btn-primary" onClick={proceed}>
              Continue to the {DISEASE_NAMES[disease].toLowerCase()} form
            </button>
          </div>
        </section>
      )}
    </div>
  )
}
