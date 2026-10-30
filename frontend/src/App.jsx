import { lazy, Suspense } from 'react'
import { Link, Route, Routes } from 'react-router-dom'
import AppShell from './components/AppShell'
import { homeFor, ProtectedRoute, Spinner } from './components/common'
import { useAuth } from './context/AuthContext'
import { LoginPage, RegisterPage } from './pages/AuthPages'
import Landing from './pages/Landing'

// Authenticated pages are code-split so the landing and sign-in pages load fast.
const Dashboard = lazy(() => import('./pages/Dashboard'))
const ModelsPage = lazy(() => import('./pages/Models'))
const OcrPage = lazy(() => import('./pages/Ocr'))
const ProfilePage = lazy(() => import('./pages/Profile'))
const ReportPage = lazy(() => import('./pages/Report'))
const DiseaseSelect = lazy(() => import('./pages/Assess').then((m) => ({ default: m.DiseaseSelect })))
const AssessmentPage = lazy(() => import('./pages/Assess').then((m) => ({ default: m.AssessmentPage })))
const HistoryPage = lazy(() => import('./pages/Results').then((m) => ({ default: m.HistoryPage })))
const ResultPage = lazy(() => import('./pages/Results').then((m) => ({ default: m.ResultPage })))
const AdminOverview = lazy(() => import('./pages/Admin').then((m) => ({ default: m.AdminOverview })))
const AdminPatients = lazy(() => import('./pages/Admin').then((m) => ({ default: m.AdminPatients })))
const AdminAssessments = lazy(() => import('./pages/Admin').then((m) => ({ default: m.AdminAssessments })))
const AdminAnalysis = lazy(() => import('./pages/AdminAnalysis'))
const AdminAssessment = lazy(() => import('./pages/AdminAssessment'))

function NotFound() {
  const { user } = useAuth()
  return (
    <div className="page page-narrow">
      <h1>Page not found</h1>
      <p className="muted">The address may be mistyped, or the record may have been deleted.</p>
      <Link className="btn btn-primary" to={homeFor(user)}>Go to {user?.role === 'admin' ? 'overview' : 'dashboard'}</Link>
    </div>
  )
}

const patient = (el) => <ProtectedRoute role="patient">{el}</ProtectedRoute>
const admin = (el) => <ProtectedRoute role="admin">{el}</ProtectedRoute>

export default function App() {
  return (
    <Suspense fallback={<Spinner />}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
          {/* Patient area */}
          <Route path="/dashboard" element={patient(<Dashboard />)} />
          <Route path="/assess" element={patient(<DiseaseSelect />)} />
          <Route path="/assess/:disease" element={patient(<AssessmentPage />)} />
          <Route path="/results/:id" element={patient(<ResultPage />)} />
          <Route path="/history" element={patient(<HistoryPage />)} />
          <Route path="/reports/:id" element={patient(<ReportPage />)} />
          <Route path="/ocr" element={patient(<OcrPage />)} />
          {/* Administrator area */}
          <Route path="/admin" element={admin(<AdminOverview />)} />
          <Route path="/admin/patients" element={admin(<AdminPatients />)} />
          <Route path="/admin/assessments" element={admin(<AdminAssessments />)} />
          <Route path="/admin/assessments/:id" element={admin(<AdminAssessment />)} />
          <Route path="/admin/reports/:id" element={admin(<ReportPage admin />)} />
          <Route path="/admin/analysis" element={admin(<AdminAnalysis />)} />
          {/* Both */}
          <Route path="/models" element={<ModelsPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
