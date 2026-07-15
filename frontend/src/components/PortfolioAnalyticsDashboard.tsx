import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { PageHeader, Skeleton } from './ui'
import type { Portfolio } from '../lib/types'

type MetricsResponse = {
  factor_exposure: Record<string, string>
  tracking_error: string
  information_ratio: string
  sharpe_ratio: string | null
  available?: boolean
  reason?: string
}

export default function PortfolioAnalyticsDashboard({ portfolioId: propId }: { portfolioId?: string }) {
  const { portfolioId: routeId } = useParams<{ portfolioId: string }>()
  const portfolioId = propId ?? routeId
  const { data: portfolio } = useQuery({
    queryKey: ['portfolio', portfolioId],
    enabled: !!portfolioId,
    queryFn: () => api<Portfolio>(`/portfolios/${portfolioId}`),
  })
  const { data: metrics, isLoading } = useQuery({
    queryKey: ['analytics-metrics', portfolioId],
    enabled: !!portfolioId,
    queryFn: () => api<MetricsResponse>(`/analytics/portfolios/${portfolioId}/metrics`),
  })
  const { data: exposure } = useQuery({
    queryKey: ['analytics-exposure', portfolioId],
    enabled: !!portfolioId,
    queryFn: () =>
      api<{
        sector: Record<string, string>
        country: Record<string, string>
        note?: string
      }>(`/analytics/portfolios/${portfolioId}/exposure`),
  })

  const metricsAvailable = metrics?.available === true

  return (
    <div className="space-y-4">
      <PageHeader title="Portfolio analytics" sub={portfolio?.name} />
      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          <div className="terminal-card p-4">
            <p className="text-xs text-ink-400">Tracking error</p>
            <p className="font-mono text-xl text-volt-300">
              {metricsAvailable ? (metrics?.tracking_error ?? '—') : '—'}
            </p>
          </div>
          <div className="terminal-card p-4">
            <p className="text-xs text-ink-400">Information ratio</p>
            <p className="font-mono text-xl text-volt-300">
              {metricsAvailable ? (metrics?.information_ratio ?? '—') : '—'}
            </p>
          </div>
          <div className="terminal-card p-4">
            <p className="text-xs text-ink-400">Sectors</p>
            <p className="text-sm text-ink-200">
              {Object.keys(exposure?.sector ?? {}).join(', ') || '—'}
            </p>
          </div>
        </div>
      )}
      <div className="terminal-card p-4 space-y-2">
        <p className="text-sm text-ink-300">
          {metrics?.reason ??
            'Extended factor metrics require a historical return series. Holdings snapshots alone are not used to invent performance curves.'}
        </p>
        {exposure?.note ? <p className="text-xs text-ink-500">{exposure.note}</p> : null}
      </div>
    </div>
  )
}
