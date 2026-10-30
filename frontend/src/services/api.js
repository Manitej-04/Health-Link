import axios from 'axios'

// All requests go to /api on the same origin (Vite proxies to Flask in dev).
// The JWT lives in an HttpOnly cookie the browser sends automatically; the
// readable csrf_access_token cookie is echoed in a header (double-submit CSRF).
const api = axios.create({ baseURL: '/api', withCredentials: true, timeout: 60000 })

function readCookie(name) {
  const match = document.cookie.split('; ').find((c) => c.startsWith(`${name}=`))
  return match ? decodeURIComponent(match.split('=').slice(1).join('=')) : null
}

api.interceptors.request.use((config) => {
  const method = (config.method || 'get').toLowerCase()
  if (!['get', 'head', 'options'].includes(method)) {
    const csrf = readCookie('csrf_access_token')
    if (csrf) config.headers['X-CSRF-TOKEN'] = csrf
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status
    const code = err.response?.data?.error?.code
    const isAuthCall = err.config?.url?.startsWith('/auth/login') || err.config?.url?.startsWith('/auth/register')
    if (status === 401 && !isAuthCall && code !== 'invalid_credentials') {
      window.dispatchEvent(new CustomEvent('healthlink:unauthorized', { detail: code }))
    }
    return Promise.reject(err)
  },
)

/** Turn any axios error into { message, details, status, code }. */
export function apiError(err) {
  const e = err?.response?.data?.error
  if (e) return { message: e.message, details: e.details || {}, status: err.response.status, code: e.code }
  if (err?.code === 'ECONNABORTED') return { message: 'The server took too long to respond.', details: {}, status: 0 }
  return { message: 'Cannot reach the Health-Link server. Check that the backend is running.', details: {}, status: 0 }
}

const data = (p) => p.then((r) => r.data.data)

export const authApi = {
  register: (body) => data(api.post('/auth/register', body)),
  login: (body) => data(api.post('/auth/login', body)),
  logout: () => data(api.post('/auth/logout')),
  me: () => data(api.get('/auth/me')),
  updateProfile: (body) => data(api.patch('/auth/me', body)),
  changePassword: (body) => data(api.post('/auth/change-password', body)),
}

export const modelApi = {
  list: () => data(api.get('/models')),
  health: () => data(api.get('/health')),
}

export const predictionApi = {
  predict: (disease, features, source = 'manual') => data(api.post(`/predict/${disease}`, { features, source })),
  history: (params) => data(api.get('/history', { params })),
  summary: () => data(api.get('/history/summary')),
  get: (id) => data(api.get(`/history/${id}`)),
  remove: (id) => data(api.delete(`/history/${id}`)),
  report: (id) => data(api.get(`/reports/${id}`)),
}

export const ocrApi = {
  extract: (disease, file) => {
    const form = new FormData()
    form.append('disease', disease)
    form.append('file', file)
    return data(api.post('/ocr/extract', form, { headers: { 'Content-Type': 'multipart/form-data' } }))
  },
}

export const adminApi = {
  stats: () => data(api.get('/admin/stats')),
  users: () => data(api.get('/admin/users')),
  updateUser: (id, body) => data(api.patch(`/admin/users/${id}`, body)),
  user: (id) => data(api.get(`/admin/users/${id}`)),
  predictions: (params) => data(api.get('/admin/predictions', { params })),
  prediction: (id) => data(api.get(`/admin/predictions/${id}`)),
  report: (id) => data(api.get(`/admin/reports/${id}`)),
  analytics: () => data(api.get('/admin/analytics')),
}

export default api
