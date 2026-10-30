/**
 * Client-side mirror of the backend's schema validation. It exists for fast
 * feedback only — the server re-validates every request independently.
 *
 * values:  { fieldName: string }        raw input values
 * unavailable: Set of optional fields the user explicitly marked "not available"
 * returns { errors, payload } where payload maps field -> number | null
 */
export function validateForm(features, values, unavailable = new Set()) {
  const errors = {}
  const payload = {}
  for (const f of features) {
    const raw = values[f.name]
    const empty = raw === undefined || raw === null || String(raw).trim() === ''
    if (!f.required && unavailable.has(f.name)) {
      payload[f.name] = null
      continue
    }
    if (empty) {
      errors[f.name] = f.required ? 'This field is required.' : 'Enter a value or mark it as not available.'
      continue
    }
    const num = Number(raw)
    if (!Number.isFinite(num)) {
      errors[f.name] = 'Must be a number.'
      continue
    }
    if (f.type === 'select') {
      if (!f.options.some((o) => Math.abs(Number(o.value) - num) < 1e-9)) {
        errors[f.name] = 'Choose one of the listed options.'
        continue
      }
    } else {
      if (f.type === 'integer' && !Number.isInteger(num)) {
        errors[f.name] = 'Must be a whole number.'
        continue
      }
      if (num < f.min || num > f.max) {
        errors[f.name] = `Must be between ${f.min} and ${f.max}${f.unit ? ` ${f.unit}` : ''}.`
        continue
      }
    }
    payload[f.name] = num
  }
  return { errors, payload }
}
