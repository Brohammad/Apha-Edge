import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Trophy } from 'lucide-react'
import { api } from '../lib/api'
import { fmtNum } from '../lib/format'
import { ErrorNote, PageHeader, Skeleton, StatCard, StatusBadge } from '../components/ui'
import type { OptimizationRun, OptimizationTrial, Paginated } from '../lib/types'

export default function OptimizationDetailPage() {
  const { runId } = useParams<{ runId: string }>()

  const { data: run } = useQuery({
    queryKey: ['optimization', runId],
    queryFn: () => api<OptimizationRun>(`/optimization-runs/${runId}`),
    refetchInterval: (q) => {
      const s = q.state.data?.status
      return s === 'queued' || s === 'running' ? 4_000 : false
    },
  })

  const { data: trials } = useQuery({
    queryKey: ['optimization-trials', runId],
    queryFn: () => api<Paginated<OptimizationTrial>>(`/optimization-runs/${runId}/trials`),
    refetchInterval: run && (run.status === 'queued' || run.status === 'running') ? 6_000 : false,
  })

  if (!run) {
    return (
      <div className="mx-auto max-w-6xl space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  const items = [...(trials?.items ?? [])].sort((a, b) => {
    if (a.rank !== null && b.rank !== null) return a.rank - b.rank
    if (a.rank !== null) return -1
    if (b.rank !== null) return 1
    return 0
  })
  const paramKeys = Array.from(new Set(items.flatMap((t) => Object.keys(t.parameters))))
  const pct = run.total_trials > 0 ? (run.completed_trials / run.total_trials) * 100 : 0

  return (
    <div className="mx-auto max-w-6xl">
      <Link
        to="/optimizations"
        className="mb-3 inline-flex items-center gap-1 text-sm text-ink-300 hover:text-volt-300"
      >
        <ArrowLeft size={14} /> Optimizer
      </Link>
      <PageHeader
        title={run.name}
        sub={`${run.method.replace('_', ' ')} · objective: ${run.objective.replace('_', ' ')}`}
        actions={<StatusBadge status={run.status} />}
      />

      {run.error_message && (
        <div className="mb-6">
          <ErrorNote message={run.error_message} />
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Total trials" value={run.total_trials} />
        <StatCard label="Completed" value={run.completed_trials} accent="volt" />
        <StatCard
          label="Progress"
          value={`${pct.toFixed(0)}%`}
          sub={
            <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-ink-700">
              <div
                className="h-full rounded-full bg-gradient-to-r from-volt-500 to-bull-500 transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
          }
        />
        <StatCard
          label="Best objective"
          value={fmtNum(items.find((t) => t.rank === 1)?.objective_value ?? null, 3)}
          accent="bull"
        />
      </div>

      <div className="terminal-card mt-6 overflow-x-auto">
        <div className="border-b border-ink-700 px-4 py-3">
          <p className="font-mono text-[11px] uppercase tracking-widest text-ink-300">
            Trials leaderboard
          </p>
        </div>
        {items.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-ink-400">No trials yet.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-ink-700 font-mono text-[11px] uppercase tracking-widest text-ink-300">
                <th className="px-4 py-2.5 font-medium">Rank</th>
                {paramKeys.map((k) => (
                  <th key={k} className="px-4 py-2.5 font-medium">
                    {k}
                  </th>
                ))}
                <th className="px-4 py-2.5 text-right font-medium">Objective</th>
                <th className="px-4 py-2.5 text-right font-medium">In-sample</th>
                <th className="px-4 py-2.5 font-medium">Status</th>
                <th className="px-4 py-2.5 font-medium">Backtest</th>
              </tr>
            </thead>
            <tbody className="font-mono text-xs">
              {items.map((t) => (
                <tr
                  key={t.id}
                  className={`border-b border-ink-800 last:border-0 ${
                    t.rank === 1 ? 'bg-bull-500/5' : ''
                  }`}
                >
                  <td className="px-4 py-2.5">
                    {t.rank === 1 ? (
                      <span className="inline-flex items-center gap-1.5 font-semibold text-gold-400">
                        <Trophy size={13} /> #1
                      </span>
                    ) : t.rank !== null ? (
                      <span className="text-ink-200">#{t.rank}</span>
                    ) : (
                      <span className="text-ink-400">—</span>
                    )}
                  </td>
                  {paramKeys.map((k) => (
                    <td key={k} className="px-4 py-2.5 text-ink-200">
                      {String(t.parameters[k] ?? '—')}
                    </td>
                  ))}
                  <td className="px-4 py-2.5 text-right text-ink-100">
                    {fmtNum(t.objective_value, 3)}
                  </td>
                  <td className="px-4 py-2.5 text-right text-ink-300">
                    {fmtNum(t.in_sample_objective, 3)}
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={t.status} />
                  </td>
                  <td className="px-4 py-2.5">
                    {t.backtest_run_id ? (
                      <Link
                        to={`/backtests/${t.backtest_run_id}`}
                        className="text-volt-400 hover:text-volt-300"
                      >
                        view →
                      </Link>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
