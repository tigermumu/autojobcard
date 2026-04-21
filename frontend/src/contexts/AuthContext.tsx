import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { authApi, UserProfile } from '../services/authApi'
import { clearAuthToken, getAuthToken, getAuthUnauthorizedEventName, setAuthToken } from '../services/api'

interface AuthContextValue {
  user: UserProfile | null
  loading: boolean
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  refreshMe: () => Promise<void>
  hasPermission: (permission: string) => boolean
  hasAnyPermission: (permissions: string[]) => boolean
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)

  const logout = useCallback(() => {
    clearAuthToken()
    setUser(null)
  }, [])

  const refreshMe = useCallback(async () => {
    const token = getAuthToken()
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }

    try {
      const currentUser = await authApi.me()
      setUser(currentUser)
    } catch {
      clearAuthToken()
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshMe()
  }, [refreshMe])

  useEffect(() => {
    const eventName = getAuthUnauthorizedEventName()
    const handler = () => logout()
    window.addEventListener(eventName, handler)
    return () => window.removeEventListener(eventName, handler)
  }, [logout])

  const login = useCallback(async (username: string, password: string) => {
    const result = await authApi.login({ username, password })
    setAuthToken(result.access_token)
    setUser(result.user)
  }, [])

  const hasPermission = useCallback(
    (permission: string) => Boolean(user?.is_superuser || user?.permissions?.includes(permission)),
    [user]
  )

  const hasAnyPermission = useCallback(
    (permissions: string[]) => Boolean(user?.is_superuser || permissions.some((item) => user?.permissions?.includes(item))),
    [user]
  )

  const value = useMemo<AuthContextValue>(() => ({
    user,
    loading,
    isAuthenticated: Boolean(user),
    login,
    logout,
    refreshMe,
    hasPermission,
    hasAnyPermission,
  }), [user, loading, login, logout, refreshMe, hasPermission, hasAnyPermission])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth 必须在 AuthProvider 内使用')
  }
  return context
}
