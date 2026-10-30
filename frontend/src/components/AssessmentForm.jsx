import { useState } from 'react'
import { LoaderCircle, ScanText } from 'lucide-react'
import { validateForm } from '../utils/validation'

function Field({ f, value, error, unavailable, fromReport, onChange, onToggleUnavailable, disabled }) {
  const id = `f-${f.name}`
  const describedBy = [f.help && `${id}-help`, error && `${id}-err`].filter(Boolean).join(' ') || undefined
  const range = f.type !== 'select' ? `${f.min}–${f.max}${f.unit ? ` ${f.unit}` : ''}` : null
  return (
    <div className={`field ${error ? 'has-error' : ''} ${fromReport ? 'from-report' : ''}`}>
      <label htmlFor={id}>
        {f.label}
        {!f.required && <span className="optional"> (optional)</span>}
      </label>
      {f.type === 'select' ? (
        <select id={id} value={value ?? ''} onChange={(e) => onChange(f.name, e.target.value)} aria-invalid={!!error}
          aria-describedby={describedBy} disabled={disabled || unavailable}>
          <option value="">Select…</option>
          {f.options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      ) : (
        <div className="input-unit">
          <input id={id} type="number" inputMode="decimal" step={f.type === 'integer' ? 1 : 'any'} min={f.min} max={f.max}
            value={value ?? ''} onChange={(e) => onChange(f.name, e.target.value)} aria-invalid={!!error}
            aria-describedby={describedBy} disabled={disabled || unavailable} placeholder={range} />
          {f.unit && <span className="unit">{f.unit}</span>}
        </div>
      )}
      {fromReport && !error && (
        <p className="field-note">
          <ScanText size={14} aria-hidden="true" /> Read from your report — check it matches.
        </p>
      )}
      {f.help && (
        <p className="field-help" id={`${id}-help`}>
          {f.help}
        </p>
      )}
      {!f.required && (
        <label className="check">
          <input type="checkbox" checked={unavailable} onChange={() => onToggleUnavailable(f.name)} disabled={disabled} />
          Not available
        </label>
      )}
      {error && (
        <p className="field-error" id={`${id}-err`} role="alert">
          {error}
        </p>
      )}
    </div>
  )
}

/** Form generated from the model's own input schema (served by /api/models). */
export default function AssessmentForm({ module, initialValues = {}, reportFields = [], onSubmit, serverErrors = {} }) {
  const [values, setValues] = useState(() =>
    Object.fromEntries(Object.entries(initialValues).map(([k, v]) => [k, v === null || v === undefined ? '' : String(v)])),
  )
  const [unavailable, setUnavailable] = useState(new Set())
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const allErrors = { ...serverErrors, ...errors }

  const onChange = (name, v) => {
    setValues((s) => ({ ...s, [name]: v }))
    setErrors((e) => ({ ...e, [name]: undefined }))
  }
  const onToggleUnavailable = (name) => {
    setUnavailable((s) => {
      const n = new Set(s)
      n.has(name) ? n.delete(name) : n.add(name)
      return n
    })
    setErrors((e) => ({ ...e, [name]: undefined }))
  }

  const submit = async (e) => {
    e.preventDefault()
    if (submitting) return
    const { errors: errs, payload } = validateForm(module.features, values, unavailable)
    setErrors(errs)
    if (Object.keys(errs).length) {
      document.getElementById(`f-${Object.keys(errs)[0]}`)?.focus()
      return
    }
    setSubmitting(true)
    try {
      await onSubmit(payload)
    } finally {
      setSubmitting(false)
    }
  }

  const required = module.features.filter((f) => f.required)
  const optional = module.features.filter((f) => !f.required)

  return (
    <form className="assessment-form" onSubmit={submit} noValidate>
      <fieldset disabled={submitting}>
        <legend className="sr-only">{module.name} inputs</legend>
        <div className="field-grid">
          {required.map((f) => (
            <Field key={f.name} f={f} value={values[f.name]} error={allErrors[f.name]} unavailable={false}
              fromReport={reportFields.includes(f.name)} onChange={onChange} onToggleUnavailable={onToggleUnavailable} />
          ))}
        </div>
        {optional.length > 0 && (
          <div className="optional-block">
            <h3>Optional measurements</h3>
            <p className="muted small">
              These were often missing in the training data. If you mark one as not available, the model uses the median
              value from its training data and the result will say so.
            </p>
            <div className="field-grid">
              {optional.map((f) => (
                <Field key={f.name} f={f} value={values[f.name]} error={allErrors[f.name]} unavailable={unavailable.has(f.name)}
                  fromReport={reportFields.includes(f.name)} onChange={onChange} onToggleUnavailable={onToggleUnavailable} />
              ))}
            </div>
          </div>
        )}
      </fieldset>
      <div className="form-actions">
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? (
            <>
              <LoaderCircle className="spin" size={18} aria-hidden="true" /> Running the model…
            </>
          ) : (
            'Get assessment'
          )}
        </button>
      </div>
    </form>
  )
}
