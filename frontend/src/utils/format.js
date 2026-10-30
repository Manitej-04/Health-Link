import { Bean, Droplet, FlaskConical, HeartPulse } from 'lucide-react'

export const DISEASE_META = {
  heart: { icon: HeartPulse, tone: 'heart', blurb: 'Cardiac stress-test and lipid measurements' },
  diabetes: { icon: Droplet, tone: 'diabetes', blurb: 'Glucose tolerance, BMI and family history' },
  kidney: { icon: Bean, tone: 'kidney', blurb: 'Urinalysis, blood chemistry and haematology' },
  liver: { icon: FlaskConical, tone: 'liver', blurb: 'Liver function panel: bilirubin, enzymes, proteins' },
}

export const DISEASE_ORDER = ['heart', 'diabetes', 'kidney', 'liver']

export const DISEASE_NAMES = {
  heart: 'Heart Disease',
  diabetes: 'Diabetes',
  kidney: 'Chronic Kidney Disease',
  liver: 'Liver Disease',
}

export const RISK_TEXT = {
  LOW: 'Low',
  MODERATE: 'Moderate',
  HIGH: 'High',
}

export function formatPercent(p, digits = 1) {
  if (p === null || p === undefined) return '—'
  return `${(p * 100).toFixed(digits)}%`
}

export function formatDate(iso, withTime = true) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    ...(withTime ? { hour: '2-digit', minute: '2-digit' } : {}),
  })
}

export function formatMetric(v, digits = 3) {
  return v === null || v === undefined ? '—' : Number(v).toFixed(digits)
}

export const STATUS_TEXT = {
  available: 'Available',
  experimental: 'Experimental',
  unavailable: 'Unavailable',
}

/**
 * Build the object RiskResultCard renders from a stored prediction (history
 * endpoint) plus the module info from /api/models. Used when the result page
 * is opened directly rather than straight after a prediction.
 */
export function resultFromPrediction(pred, module, riskBands) {
  const name = module?.name || DISEASE_NAMES[pred.disease]
  const hasProb = pred.probability !== null && pred.probability !== undefined
  const band = hasProb ? riskBands?.find((b) => b.category === pred.risk_category) : null
  return {
    id: pred.id,
    disease: pred.disease,
    disease_name: name,
    predicted_class: pred.predicted_class,
    predicted_label: pred.predicted_label,
    probability: pred.probability,
    risk_category: pred.risk_category,
    risk_bands: hasProb ? riskBands : null,
    model_status: pred.model_status,
    model_algorithm: pred.model_algorithm,
    created_at: pred.created_at,
    factors: pred.factors,
    not_provided: (pred.not_provided || []).map((f) => ({
      feature: f,
      label: module?.features?.find((x) => x.name === f)?.label || f,
    })),
    explanation: hasProb
      ? `The ${pred.model_algorithm} model estimated a ${formatPercent(pred.probability)} probability that this profile resembles patients with ${name.toLowerCase()} in its training data. This falls in Health-Link's application-defined ${pred.risk_category} band${band ? ` (${band.range})` : ''}, which is educational and not a clinical threshold.`
      : 'This module reports the model\'s predicted class only. A probability and a LOW/MODERATE/HIGH band are not shown, because the module did not meet Health-Link\'s criteria for trustworthy probabilities.',
    risk_unavailable_reason: hasProb ? null : module?.probability_reason,
    experimental_notice:
      pred.model_status === 'experimental'
        ? `This module is EXPERIMENTAL. ${(module?.status_reasons || []).join('; ')}`
        : null,
    imputation_notice: pred.not_provided?.length
      ? 'Some optional values were not provided; the model substituted the median value from its training data, which makes this estimate less reliable.'
      : null,
  }
}
