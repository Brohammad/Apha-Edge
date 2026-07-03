import Constants from 'expo-constants'
import * as SecureStore from 'expo-secure-store'

const BASE =
  (Constants.expoConfig?.extra?.apiBaseUrl as string | undefined) ??
  'https://localhost:8000/api/v1'

const TOKEN_KEY = 'alphaedge.tokens'
const CLIENT_HEADER = { 'X-Client-Type': 'mobile' }

export interface TokenPair {
  access_token: string
  refresh_token: string
}

export async function loadTokens(): Promise<TokenPair | null> {
  const raw = await SecureStore.getItemAsync(TOKEN_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as TokenPair
  } catch {
    return null
  }
}

export async function saveTokens(tokens: TokenPair | null): Promise<void> {
  if (tokens) {
    await SecureStore.setItemAsync(TOKEN_KEY, JSON.stringify(tokens))
  } else {
    await SecureStore.deleteItemAsync(TOKEN_KEY)
  }
}

let refreshPromise: Promise<boolean> | null = null

async function tryRefresh(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const tokens = await loadTokens()
      if (!tokens?.refresh_token) return false
      const res = await fetch(`${BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...CLIENT_HEADER },
        body: JSON.stringify({ refresh_token: tokens.refresh_token }),
      })
      if (!res.ok) return false
      const json = await res.json()
      const pair = json.data as TokenPair
      if (!pair.refresh_token) {
        pair.refresh_token = tokens.refresh_token
      }
      await saveTokens(pair)
      return true
    })().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

export async function api<T>(
  path: string,
  opts: { method?: string; body?: unknown; auth?: boolean } = {},
): Promise<T> {
  const { method = 'GET', body, auth = true } = opts

  const doFetch = async () => {
    const headers: Record<string, string> = { ...CLIENT_HEADER }
    if (body !== undefined) headers['Content-Type'] = 'application/json'
    if (auth) {
      const tokens = await loadTokens()
      if (tokens) headers['Authorization'] = `Bearer ${tokens.access_token}`
    }
    return fetch(`${BASE}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  }

  let res = await doFetch()
  if (res.status === 401 && auth) {
    const refreshed = await tryRefresh()
    if (refreshed) {
      res = await doFetch()
    } else {
      await saveTokens(null)
      throw new Error('Session expired')
    }
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err?.error?.message ?? `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  const json = await res.json()
  return json.data as T
}
