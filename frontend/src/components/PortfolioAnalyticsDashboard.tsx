import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { PageHeader, Skeleton } from './ui'
import { DrawdownChart } from './institutionalCharts'
import { EquitySparkline, type SeriesPoint } from './charts'
import type { Portfolio } from '../lib/types'

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
    queryFn: () =>
      api<{
        factor_exposure: Record<string, string>
        tracking_error: string
        information_ratio: string
      }>(`/analytics/portfolios/${portfolioId}/metrics`),
  })
  const { data: exposure } = useQuery({
    queryKey: ['analytics-exposure', portfolioId],
    enabled: !!portfolioId,
    queryFn: () =>
      api<{ sector: Record<string, string>; country: Record<string, string> }>(
        `/analytics/portfolios/${portfolioId}/exposure`,
      ),
  })

  const mockCurve: SeriesPoint[] = Array.from({ length: 30 }, (_, i) => ({
    ts: new Date(Date.now() - (29 - i) * 86400000).toISOString(),
    value: Number(portfolio?.initial_capital ?? 100000) * (1 + i * 0.002),
  }))

  return (
    <div className="space-y-4">
      <PageHeader title="Portfolio analytics" sub={portfolio?.name} />
      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          <div className="terminal-card p-4">
            <p className="text-xs text-ink-400">Tracking error</p>
            <p className="font-mono text-xl text-volt-300">{metrics?.tracking_error ?? '—'}</p>
          </div>
          <div className="terminal-card p-4">
            <p className="text-xs text-ink-400">Information ratio</p>
            <p className="font-mono text-xl text-volt-300">{metrics?.information_ratio ?? '—'}</p>
          </div>
          <div className="terminal-card p-4">
            <p className="text-xs text-ink-400">Sectors</p>
            <p className="text-sm text-ink-200">
              {Object.keys(exposure?.sector ?? {}).join(', ') || '—'}
            </p>
          </div>
        </div>
      )}
      <div className="terminal-card p-4">
        <EquitySparkline data={mockCurve} />
        <DrawdownChart data={mockCurve} />
      </div>
    </div>
  )
}
