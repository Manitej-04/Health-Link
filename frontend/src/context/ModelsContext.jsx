import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { apiError, modelApi } from '../services/api'

const ModelsContext = createContext(null)

/** Loads /api/models once: module status, input schemas, risk bands, disclaimer. */
export function ModelsProvider({ children }) {
  const [state, setState] = useState({ loading: true, error: null, modules: [], riskBands: [], disclaimer: '' })

  const load = useCallback(() => {
    setState((s) => ({ ...s, loading: true, error: null }))
    modelApi
      .list()
      .then((d) => setState({ loading: false, error: null, modules: d.modules, riskBands: d.risk_bands, disclaimer: d.disclaimer }))
      .catch((e) => setState((s) => ({ ...s, loading: false, error: apiError(e).message })))
  }, [])

  useEffect(load, [load])

  const getModule = (key) => state.modules.find((m) => m.key === key)
  return <ModelsContext.Provider value={{ ...state, reload: load, getModule }}>{children}</ModelsContext.Provider>
}

export function useModels() {
  const ctx = useContext(ModelsContext)
  if (!ctx) throw new Error('useModels must be used inside ModelsProvider')
  return ctx
}
