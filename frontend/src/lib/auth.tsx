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
  completeOAuthLogin: (accessToken: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function readOAuthAccessToken(): string | null {
  const hash = window.location.hash.startsWith('#')
    ? window.location.hash.slice(1)
    : window.location.hash
  const params = new URLSearchParams(hash)
  return params.get('access_token')
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null))

    const bootstrap = async () => {
      const oauthAccess = readOAuthAccessToken()
      if (oauthAccess) {
        saveTokens({ access_token: oauthAccess, refresh_token: '', token_type: 'bearer' })
        window.history.replaceState(null, '', window.location.pathname)
      }

      if (!loadTokens() && !oauthAccess) {
        const refreshed = await fetch('/api/v1/auth/refresh', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: '' }),
        })
        if (refreshed.ok) {
          const body = (await refreshed.json()) as { data: TokenPair }
          saveTokens(body.data)
        }
      }

      if (!loadTokens()) {
        setLoading(false)
        return
      }

      try {
        setUser(await api<User>('/auth/me'))
      } catch {
        saveTokens(null)
      } finally {
        setLoading(false)
      }
    }

    void bootstrap()
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

  const completeOAuthLogin = useCallback(async (accessToken: string) => {
    saveTokens({ access_token: accessToken, token_type: 'bearer' })
    setUser(await api<User>('/auth/me'))
  }, [])

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
