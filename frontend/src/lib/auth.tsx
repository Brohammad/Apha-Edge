import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api, loadTokens, saveTokens, setSessionExpiredHandler } from './api'
import type { TokenPair, User } from './types'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, displayName: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null))
    if (!loadTokens()) {
      setLoading(false)
      return
    }
    api<User>('/auth/me')
      .then(setUser)
      .catch(() => saveTokens(null))
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await api<TokenPair>('/auth/login', {
      method: 'POST',
      body: { email, password },
      auth: false,
    })
    saveTokens(tokens)
    setUser(await api<User>('/auth/me'))
  }, [])

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

  const logout = useCallback(async () => {
    const tokens = loadTokens()
    if (tokens?.refresh_token) {
      await api('/auth/logout', {
        method: 'POST',
        body: { refresh_token: tokens.refresh_token },
        auth: false,
      }).catch(() => {})
    }
    saveTokens(null)
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
