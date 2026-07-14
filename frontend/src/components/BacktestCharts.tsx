import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { DrawdownChart, ReturnsHistogram } from '../components/institutionalCharts'
import { EquitySparkline, type SeriesPoint } from '../components/charts'
import { PageHeader, Skeleton } from '../components/ui'
import type { BacktestRun, EquityPoint, Paginated } from '../lib/types'

export default function BacktestAnalyticsPage({ runId }: { runId: string }) {
  const { data: curve, isLoading } = useQuery({
    queryKey: ['equity-curve', runId],
    queryFn: () => api<Paginated<EquityPoint>>(`/backtest-runs/${runId}/equity-curve`),
  })

  const points: SeriesPoint[] = (curve?.items ?? []).map((p) => ({
    ts: p.timestamp,
    value: Number(p.equity),
  }))
  const returns = points.slice(1).map((p, i) => (p.value - points[i].value) / points[i].value)

  if (isLoading) return <Skeleton className="h-80 w-full" />

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="terminal-card p-4">
        <h3 className="mb-2 text-sm font-medium text-ink-200">Equity curve</h3>
        <EquitySparkline data={points} height={240} />
      </div>
      <div className="terminal-card p-4">
        <h3 className="mb-2 text-sm font-medium text-ink-200">Drawdown</h3>
        <DrawdownChart data={points} height={240} />
      </div>
      <div className="terminal-card p-4 lg:col-span-2">
        <h3 className="mb-2 text-sm font-medium text-ink-200">Return distribution</h3>
        <ReturnsHistogram returns={returns} />
      </div>
    </div>
  )
}

export function BacktestChartsSection({ runId }: { runId: string }) {
  return <BacktestAnalyticsPage runId={runId} />
}
