import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { PageHeader, Skeleton } from './ui'

export default function WalkForwardChart({ runId: runIdProp }: { runId?: string }) {
  const { runId: routeRunId } = useParams<{ runId: string }>()
  const runId = runIdProp ?? routeRunId
  const { data, isLoading } = useQuery({
    queryKey: ['walk-forward', runId],
    enabled: !!runId,
    queryFn: () =>
      api<{ windows: Array<{ window: number; in_sample_sharpe: number; out_sample_sharpe: number }> }>(
        `/optimization/walk-forward/${runId}`,
      ),
  })

  if (isLoading) return <Skeleton className="h-48 w-full" />

  return (
    <div className="terminal-card p-4">
      <PageHeader title="Walk-forward analysis" sub={`Run ${runId?.slice(0, 8)}`} />
      <div className="space-y-2">
        {(data?.windows ?? []).map((w) => (
          <div key={w.window} className="flex justify-between font-mono text-sm text-ink-200">
            <span>Window {w.window}</span>
            <span>IS {w.in_sample_sharpe.toFixed(2)} / OOS {w.out_sample_sharpe.toFixed(2)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
