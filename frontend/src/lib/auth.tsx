import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api, saveTokens, setSessionExpiredHandler } from './api'
import type { User } from './types'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, displayName: string) => Promise<void>
  completeOAuthLogin: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const loadCurrentUser = useCallback(async () => {
    try {
      setUser(await api<User>('/auth/me'))
      return true
    } catch {
      setUser(null)
      return false
    }
  }, [])

  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null))

    const bootstrap = async () => {
      const params = new URLSearchParams(window.location.search)
      if (params.get('oauth') === 'success') {
        window.history.replaceState(null, '', window.location.pathname)
      }

      const ok = await loadCurrentUser()
      if (!ok) {
        const refreshed = await fetch('/api/v1/auth/refresh', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: '' }),
        })
        if (refreshed.ok) {
          await loadCurrentUser()
        }
      }
      setLoading(false)
    }

    void bootstrap()
  }, [loadCurrentUser])

  const login = useCallback(
    async (email: string, password: string) => {
      await api('/auth/login', {
        method: 'POST',
        body: { email, password },
        auth: false,
      })
      await loadCurrentUser()
    },
    [loadCurrentUser],
  )

  const register = useCallback(
    async (email: string, password: string, displayName: string) => {
      await api<User>('/auth/register', {
        method: 'POST',
        body: { email, password, display_name: displayName },
        auth: false,
      })
      await login(email, password)
    },
    [login],
  )

  const completeOAuthLogin = useCallback(async () => {
    await loadCurrentUser()
  }, [loadCurrentUser])

  const logout = useCallback(async () => {
    await api('/auth/logout', {
      method: 'POST',
      body: { refresh_token: '' },
      auth: false,
    }).catch(() => {})
    saveTokens(null)
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, register, completeOAuthLogin, logout }),
    [user, loading, login, register, completeOAuthLogin, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
