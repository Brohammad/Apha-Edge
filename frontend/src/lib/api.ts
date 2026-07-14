import type { ApiErrorBody, Envelope, TokenPair } from './types'

const BASE = '/api/v1'

export class ApiError extends Error {
  code: string
  status: number

  constructor(code: string, message: string, status: number) {
    super(message)
    this.code = code
    this.status = status
  }
}

let accessToken: string | null = null

export function loadTokens(): { access_token: string } | null {
  if (accessToken) return { access_token: accessToken }
  return { access_token: '' }
}

export function saveTokens(tokens: { access_token?: string } | null): void {
  accessToken = tokens?.access_token ?? null
}

let onSessionExpired: (() => void) | null = null

export function setSessionExpiredHandler(fn: () => void): void {
  onSessionExpired = fn
}

async function parseError(res: Response): Promise<ApiError> {
  try {
    const body = (await res.json()) as ApiErrorBody
    if (body.error) {
      return new ApiError(body.error.code, body.error.message, res.status)
    }
  } catch {
    // fall through to generic error
  }
  return new ApiError('HTTP_ERROR', `Request failed with status ${res.status}`, res.status)
}

let refreshPromise: Promise<boolean> | null = null

async function tryRefresh(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const res = await fetch(`${BASE}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: '' }),
      })
      if (!res.ok) return false
      const body = (await res.json()) as Envelope<TokenPair>
      saveTokens(body.data)
      return true
    })().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

interface RequestOptions {
  method?: string
  body?: unknown
  query?: Record<string, string | number | boolean | undefined>
  auth?: boolean
}

export async function api<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, query, auth = true } = opts

  let url = `${BASE}${path}`
  if (query) {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined) params.set(k, String(v))
    }
    const qs = params.toString()
    if (qs) url += `?${qs}`
  }

  const doFetch = () => {
    const headers: Record<string, string> = {}
    if (body !== undefined) headers['Content-Type'] = 'application/json'
    if (auth && accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`
    }
    return fetch(url, {
      method,
      headers,
      credentials: 'include',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  }

  let res = await doFetch()

  if (res.status === 401 && auth) {
    const refreshed = await tryRefresh()
    if (refreshed) {
      res = await doFetch()
    } else {
      saveTokens(null)
      onSessionExpired?.()
      throw await parseError(res)
    }
  }

  if (!res.ok) throw await parseError(res)
  if (res.status === 204) return undefined as T

  const json = (await res.json()) as Envelope<T>
  return json.data
}

export async function fetchWsTicket(): Promise<string> {
  const data = await api<{ ticket: string }>('/auth/ws-ticket', { method: 'POST' })
  return data.ticket
}
