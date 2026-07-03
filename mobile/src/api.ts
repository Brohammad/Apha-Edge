import Constants from 'expo-constants'
import * as SecureStore from 'expo-secure-store'

const BASE =
  (Constants.expoConfig?.extra?.apiBaseUrl as string | undefined) ??
  'http://localhost:8000/api/v1'

const TOKEN_KEY = 'alphaedge.tokens'

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

export async function api<T>(
  path: string,
  opts: { method?: string; body?: unknown; auth?: boolean } = {},
): Promise<T> {
  const { method = 'GET', body, auth = true } = opts
  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (auth) {
    const tokens = await loadTokens()
    if (tokens) headers['Authorization'] = `Bearer ${tokens.access_token}`
  }
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err?.error?.message ?? `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  const json = await res.json()
  return json.data as T
}
