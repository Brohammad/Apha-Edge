import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api, saveTokens } from './api'

describe('api client', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    saveTokens(null)
  })

  it('unwraps envelope data', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ data: { id: '1' }, meta: {} }),
      }),
    )
    const result = await api<{ id: string }>('/health/live', { auth: false })
    expect(result.id).toBe('1')
  })

  it('builds query strings', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ data: [], meta: {} }),
    })
    vi.stubGlobal('fetch', fetchMock)
    await api('/marketplace/listings', { auth: false, query: { q: 'sma', limit: 10 } })
    expect(String(fetchMock.mock.calls[0][0])).toContain('q=sma')
    expect(String(fetchMock.mock.calls[0][0])).toContain('limit=10')
  })

  it('raises ApiError on failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({
          error: { code: 'VALIDATION_ERROR', message: 'bad' },
        }),
      }),
    )
    await expect(api('/x', { auth: false })).rejects.toBeInstanceOf(ApiError)
  })
})
