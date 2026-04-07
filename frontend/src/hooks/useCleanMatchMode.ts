import { useCallback, useState } from 'react'

export type CleanMatchMode = 'ai' | 'local'

const STORAGE_KEY = 'clean_match_mode'

const isCleanMatchMode = (value: any): value is CleanMatchMode => {
  return value === 'ai' || value === 'local'
}

export function useCleanMatchMode(defaultMode: CleanMatchMode = 'ai') {
  const [mode, setModeState] = useState<CleanMatchMode>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (isCleanMatchMode(raw)) return raw
      return defaultMode
    } catch {
      return defaultMode
    }
  })

  const setMode = useCallback((next: CleanMatchMode) => {
    setModeState(next)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // ignore
    }
  }, [])

  return { mode, setMode }
}









