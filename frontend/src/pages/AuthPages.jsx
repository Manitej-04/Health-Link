import { useState } from 'react'
import { LoaderCircle } from 'lucide-react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import Logo from '../components/Logo'
import { DisclaimerBanner, homeFor } from '../components/common'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { apiError } from '../services/api'

function AuthLayout({ title, intro, children, footer }) {
  return (
    <div className="auth-page">
      <DisclaimerBanner />
      <div className="auth-wrap">
        <div className="auth-card">
          <Logo to="/" />
          <h1>{title}</h1>
          {intro && <p className="muted">{intro}</p>}
          {children}
          <p className="auth-footer">{footer}</p>
        </div>
      </div>
    </div>
  )
}

function TextField({ id, label, error, ...props }) {
  return (
    <div className={`field ${error ? 'has-error' : ''}`}>
      <label htmlFor={id}>{label}</label>
      <input id={id} aria-invalid={!!error} aria-describedby={error ? `${id}-err` : undefined} {...props} />
      {error && (
        <p className="field-error" id={`${id}-err`} role="alert">
          {error}
        </p>
      )}
    </div>
  )
}

export function LoginPage() {
  const { user, login, sessionExpired, clearExpired } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to={homeFor(user)} replace />

  const submit = async (e) => {
    e.preventDefault()
    if (busy) return
    if (!form.email.trim() || !form.password) {
      setError('Enter your email and password.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const u = await login(form.email.trim(), form.password)
      clearExpired()
      toast.success(`Welcome back, ${u.name.split(' ')[0]}.`)
      const from = location.state?.from
      const allowed = from && (u.role === 'admin') === from.startsWith('/admin')
      navigate(allowed ? from : homeFor(u), { replace: true })
    } catch (err) {
      setError(apiError(err).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout title="Sign in" footer={<>New to Health-Link? <Link to="/register">Create an account</Link></>}>
      {sessionExpired && (
        <p className="notice notice-info" role="status">
          Your session ended. Sign in again to continue.
        </p>
      )}
      <form onSubmit={submit} noValidate className="stack">
        <TextField id="email" label="Email" type="email" autoComplete="email" value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <TextField id="password" label="Password" type="password" autoComplete="current-password" value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })} />
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button className="btn btn-primary btn-block" disabled={busy}>
          {busy && <LoaderCircle className="spin" size={18} aria-hidden="true" />} Sign in
        </button>
      </form>
    </AuthLayout>
  )
}

export function RegisterPage() {
  const { user, register } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to={homeFor(user)} replace />

  const validate = () => {
    const e = {}
    if (form.name.trim().length < 2) e.name = 'Enter your name (at least 2 characters).'
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim())) e.email = 'Enter a valid email address.'
    if (form.password.length < 8) e.password = 'Use at least 8 characters.'
    else if (!/[A-Za-z]/.test(form.password) || !/\d/.test(form.password)) e.password = 'Include at least one letter and one number.'
    if (form.confirm !== form.password) e.confirm = 'Passwords do not match.'
    return e
  }

  const submit = async (ev) => {
    ev.preventDefault()
    if (busy) return
    const e = validate()
    setErrors(e)
    setFormError('')
    if (Object.keys(e).length) return
    setBusy(true)
    try {
      await register(form.name.trim(), form.email.trim(), form.password)
      toast.success('Account created.')
      navigate('/dashboard', { replace: true })
    } catch (err) {
      const ae = apiError(err)
      const details = Object.fromEntries(Object.entries(ae.details).map(([k, v]) => [k, Array.isArray(v) ? v[0] : v]))
      setErrors(details)
      if (!Object.keys(details).length) setFormError(ae.message)
    } finally {
      setBusy(false)
    }
  }

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  return (
    <AuthLayout title="Create your account" intro="Your assessments are private to your account."
      footer={<>Already registered? <Link to="/login">Sign in</Link></>}>
      <form onSubmit={submit} noValidate className="stack">
        <TextField id="name" label="Full name" autoComplete="name" value={form.name} onChange={set('name')} error={errors.name} />
        <TextField id="email" label="Email" type="email" autoComplete="email" value={form.email} onChange={set('email')} error={errors.email} />
        <TextField id="password" label="Password" type="password" autoComplete="new-password" value={form.password}
          onChange={set('password')} error={errors.password} />
        <TextField id="confirm" label="Confirm password" type="password" autoComplete="new-password" value={form.confirm}
          onChange={set('confirm')} error={errors.confirm} />
        <p className="muted small">At least 8 characters, with a letter and a number.</p>
        {formError && (
          <p className="form-error" role="alert">
            {formError}
          </p>
        )}
        <button className="btn btn-primary btn-block" disabled={busy}>
          {busy && <LoaderCircle className="spin" size={18} aria-hidden="true" />} Create account
        </button>
      </form>
    </AuthLayout>
  )
}
