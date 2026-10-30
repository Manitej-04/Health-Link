import { useState } from 'react'
import { PageHeader } from '../components/common'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { apiError, authApi } from '../services/api'
import { formatDate } from '../utils/format'

export default function ProfilePage() {
  const { user, setUser } = useAuth()
  const toast = useToast()
  const [name, setName] = useState(user.name)
  const [nameErr, setNameErr] = useState('')
  const [pw, setPw] = useState({ current_password: '', new_password: '', confirm: '' })
  const [pwErr, setPwErr] = useState({})
  const [busy, setBusy] = useState('')

  const saveName = async (e) => {
    e.preventDefault()
    if (name.trim().length < 2) return setNameErr('Enter at least 2 characters.')
    setBusy('name')
    try {
      const d = await authApi.updateProfile({ name: name.trim() })
      setUser(d.user)
      setNameErr('')
      toast.success('Name updated.')
    } catch (err) {
      setNameErr(apiError(err).message)
    } finally {
      setBusy('')
    }
  }

  const savePw = async (e) => {
    e.preventDefault()
    const errs = {}
    if (!pw.current_password) errs.current_password = 'Enter your current password.'
    if (pw.new_password.length < 8 || !/[A-Za-z]/.test(pw.new_password) || !/\d/.test(pw.new_password))
      errs.new_password = 'At least 8 characters, with a letter and a number.'
    if (pw.confirm !== pw.new_password) errs.confirm = 'Passwords do not match.'
    setPwErr(errs)
    if (Object.keys(errs).length) return
    setBusy('pw')
    try {
      await authApi.changePassword({ current_password: pw.current_password, new_password: pw.new_password })
      setPw({ current_password: '', new_password: '', confirm: '' })
      toast.success('Password updated.')
    } catch (err) {
      const ae = apiError(err)
      setPwErr(Object.keys(ae.details).length ? Object.fromEntries(Object.entries(ae.details).map(([k, v]) => [k, Array.isArray(v) ? v[0] : v])) : { form: ae.message })
    } finally {
      setBusy('')
    }
  }

  const pwField = (key, label, auto) => (
    <div className={`field ${pwErr[key] ? 'has-error' : ''}`}>
      <label htmlFor={key}>{label}</label>
      <input id={key} type="password" autoComplete={auto} value={pw[key]} onChange={(e) => setPw({ ...pw, [key]: e.target.value })} aria-invalid={!!pwErr[key]} />
      {pwErr[key] && <p className="field-error" role="alert">{pwErr[key]}</p>}
    </div>
  )

  return (
    <div className="page page-narrow">
      <PageHeader title="Profile" />
      <section className="panel">
        <dl className="details">
          <div><dt>Email</dt><dd>{user.email}</dd></div>
          <div><dt>Role</dt><dd>{user.role === 'admin' ? 'Administrator' : 'User'}</dd></div>
          <div><dt>Member since</dt><dd>{formatDate(user.created_at, false)}</dd></div>
        </dl>
        <form onSubmit={saveName} className="stack" noValidate>
          <div className={`field ${nameErr ? 'has-error' : ''}`}>
            <label htmlFor="pname">Name</label>
            <input id="pname" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" aria-invalid={!!nameErr} />
            {nameErr && <p className="field-error" role="alert">{nameErr}</p>}
          </div>
          <div><button className="btn btn-primary" disabled={busy === 'name'}>Save name</button></div>
        </form>
      </section>
      <section className="panel">
        <h2 className="panel-title">Change password</h2>
        <form onSubmit={savePw} className="stack" noValidate>
          {pwField('current_password', 'Current password', 'current-password')}
          {pwField('new_password', 'New password', 'new-password')}
          {pwField('confirm', 'Confirm new password', 'new-password')}
          {pwErr.form && <p className="form-error" role="alert">{pwErr.form}</p>}
          <div><button className="btn btn-primary" disabled={busy === 'pw'}>Update password</button></div>
        </form>
      </section>
    </div>
  )
}
