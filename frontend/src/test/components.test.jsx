import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import AssessmentForm from '../components/AssessmentForm'
import RiskResult from '../components/RiskResult'
import { resultFromPrediction } from '../utils/format'
import { validateForm } from '../utils/validation'

const BANDS = [
  { category: 'LOW', range: 'below 30%', min: 0, max: 0.3 },
  { category: 'MODERATE', range: '30% to below 70%', min: 0.3, max: 0.7 },
  { category: 'HIGH', range: '70% and above', min: 0.7, max: 1 },
]

const MODULE = {
  key: 'diabetes',
  name: 'Diabetes',
  features: [
    { name: 'glucose', label: 'Plasma glucose', type: 'number', unit: 'mg/dL', min: 40, max: 300, required: true },
    { name: 'age', label: 'Age', type: 'integer', unit: 'years', min: 21, max: 100, required: true },
    { name: 'insulin', label: 'Serum insulin', type: 'number', min: 10, max: 900, required: false },
    { name: 'sex', label: 'Sex', type: 'select', required: true, options: [{ value: 0, label: 'Female' }, { value: 1, label: 'Male' }] },
  ],
}

describe('RiskResult', () => {
  it('shows probability, risk word and gauge when probability is supported', () => {
    render(
      <RiskResult
        result={{ id: 1, disease: 'heart', disease_name: 'Heart Disease', predicted_class: 1, predicted_label: 'Heart disease indicated',
          probability: 0.645, risk_category: 'MODERATE', risk_bands: BANDS, model_status: 'available', explanation: 'Explained.' }}
      />,
    )
    expect(screen.getByText('Moderate', { selector: '.risk-word' })).toBeInTheDocument()
    expect(screen.getAllByText('64.5%').length).toBeGreaterThan(0)
    expect(screen.getByText('Positive')).toBeInTheDocument()
    expect(screen.getByLabelText(/Model probability 64.5%, Moderate band/)).toBeInTheDocument()
    expect(screen.getByText(/not a clinical diagnosis/)).toBeInTheDocument()
  })

  it('never shows a probability or band for class-only modules', () => {
    render(
      <RiskResult
        result={{ id: 2, disease: 'kidney', disease_name: 'Chronic Kidney Disease', predicted_class: 1, predicted_label: 'CKD indicated',
          probability: null, risk_category: null, model_status: 'experimental', explanation: 'Class only.',
          experimental_notice: 'This module is EXPERIMENTAL.', risk_unavailable_reason: 'Integrity flags.' }}
      />,
    )
    expect(screen.queryByText('%', { exact: false })).not.toBeInTheDocument()
    expect(screen.queryByText('High')).not.toBeInTheDocument()
    expect(screen.getByText('Not available for this module')).toBeInTheDocument()
    expect(screen.getByText(/EXPERIMENTAL/)).toBeInTheDocument()
  })

  it('rebuilds a stored prediction without inventing a probability', () => {
    const r = resultFromPrediction(
      { id: 3, disease: 'kidney', predicted_class: 0, predicted_label: 'x', probability: null, risk_category: null, model_status: 'experimental', not_provided: [] },
      { name: 'Chronic Kidney Disease', features: [], status_reasons: ['flag'], probability_reason: 'withheld' },
      BANDS,
    )
    expect(r.probability).toBeNull()
    expect(r.risk_bands).toBeNull()
    expect(r.risk_unavailable_reason).toBe('withheld')
  })
})

describe('validateForm', () => {
  it('flags required, range, integer and option errors', () => {
    const { errors } = validateForm(MODULE.features, { glucose: '500', age: '30.5', sex: '7' })
    expect(errors.glucose).toMatch(/between 40 and 300/)
    expect(errors.age).toMatch(/whole number/)
    expect(errors.sex).toMatch(/options/)
    expect(errors.insulin).toMatch(/not available/)
  })

  it('sends null only for optional fields explicitly marked not available', () => {
    const { errors, payload } = validateForm(MODULE.features, { glucose: '148', age: '50', sex: '0' }, new Set(['insulin']))
    expect(errors).toEqual({})
    expect(payload).toEqual({ glucose: 148, age: 50, sex: 0, insulin: null })
  })
})

describe('AssessmentForm', () => {
  it('blocks submission with errors, then submits a valid payload once', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn(() => new Promise((r) => setTimeout(r, 50)))
    render(<AssessmentForm module={MODULE} onSubmit={onSubmit} />)

    await user.click(screen.getByRole('button', { name: 'Get assessment' }))
    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getAllByText('This field is required.').length).toBe(3)

    await user.type(screen.getByLabelText('Plasma glucose'), '148')
    await user.type(screen.getByLabelText('Age'), '50')
    await user.selectOptions(screen.getByLabelText('Sex'), '1')
    await user.click(screen.getByLabelText('Not available'))
    const btn = screen.getByRole('button', { name: 'Get assessment' })
    await user.click(btn)
    await user.click(btn) // double click while submitting must not resubmit
    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith({ glucose: 148, age: 50, sex: 1, insulin: null })
  })

  it('marks values that came from an uploaded report', () => {
    render(<AssessmentForm module={MODULE} initialValues={{ glucose: 120 }} reportFields={['glucose']} onSubmit={vi.fn()} />)
    expect(screen.getByLabelText('Plasma glucose')).toHaveValue(120)
    expect(screen.getByText(/Read from your report/)).toBeInTheDocument()
  })
})
