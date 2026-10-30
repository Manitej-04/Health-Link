import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { authApi } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [sessionExpired, setSessionExpired] = useState(false)

  useEffect(() => {
    let active = true
    authApi
      .me()
      .then((d) => active && setUser(d.user))
      .catch(() => active && setUser(null))
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    const onUnauthorized = () => {
      setUser((current) => {
        if (current) setSessionExpired(true)
        return null
      })
    }
    window.addEventListener('healthlink:unauthorized', onUnauthorized)
    return () => window.removeEventListener('healthlink:unauthorized', onUnauthorized)
  }, [])

  const login = useCallback(async (email, password) => {
    const d = await authApi.login({ email, password })
    setSessionExpired(false)
    setUser(d.user)
    return d.user
  }, [])

  const register = useCallback(async (name, email, password) => {
    const d = await authApi.register({ name, email, password })
    setSessionExpired(false)
    setUser(d.user)
    return d.user
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } finally {
      setUser(null)
    }
  }, [])

  const value = useMemo(
    () => ({ user, setUser, loading, login, register, logout, sessionExpired, clearExpired: () => setSessionExpired(false) }),
    [user, loading, login, register, logout, sessionExpired],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
