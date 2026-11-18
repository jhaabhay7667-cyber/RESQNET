import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { api, clearSession, readSessionUser, saveSession } from '../services/api'
import type { Role, User } from '../types'

interface AuthContextValue {
  user: User | null
  busy: boolean
  login: (username: string, password: string) => Promise<void>
  register: (data: { username: string; email: string; password: string; role: Role }) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(readSessionUser)
  const [busy, setBusy] = useState(false)

  const authenticate = useCallback(async (action: () => Promise<{ access_token: string; refresh_token: string; user: User }>) => {
    setBusy(true)
    try {
      const session = await action()
      saveSession(session)
      setUser(session.user)
    } finally {
      setBusy(false)
    }
  }, [])

  const login = useCallback((username: string, password: string) =>
    authenticate(() => api.auth.login(username, password)), [authenticate])

  const register = useCallback((data: { username: string; email: string; password: string; role: Role }) =>
    authenticate(() => api.auth.register(data)), [authenticate])

  const logout = useCallback(async () => {
    const refresh = localStorage.getItem('resqnet.refresh')
    try {
      if (refresh) await api.auth.logout(refresh)
    } finally {
    clearSession()
    setUser(null)
    }
  }, [])

  const value = useMemo(() => ({ user, busy, login, register, logout }), [user, busy, login, register, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used within AuthProvider')
  return value
}
