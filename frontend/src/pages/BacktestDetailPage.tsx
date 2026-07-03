import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, BrainCircuit, Trash2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { fmtDateTime, fmtMoney, fmtNum, fmtPct, signClass } from '../lib/format'
import { EquitySparkline, type SeriesPoint } from '../components/charts'
import {
  ErrorNote,
  PageHeader,
  Skeleton,
  StatCard,
  StatusBadge,
  btnBear,
  btnGhost,
} from '../components/ui'
import type {
  BacktestResult,
  BacktestRun,
  BacktestTrade,
  EquityPoint,
  InsightRequest,
  Paginated,
} from '../lib/types'

export default function BacktestDetailPage() {
  const { runId } = useParams<{ runId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: run } = useQuery({
    queryKey: ['backtest', runId],
    queryFn: () => api<BacktestRun>(`/backtest-runs/${runId}`),
    refetchInterval: (q) => {
      const status = q.state.data?.status
      return status === 'queued' || status === 'running' ? 4_000 : false
    },
  })

  const done = run?.status === 'completed'

  const { data: result } = useQuery({
    queryKey: ['backtest-result', runId],
    enabled: done,
    queryFn: () => api<BacktestResult>(`/backtest-runs/${runId}/result`),
  })
  const { data: curve } = useQuery({
    queryKey: ['equity-curve', runId],
    enabled: done,
    queryFn: () => api<Paginated<EquityPoint>>(`/backtest-runs/${runId}/equity-curve`),
  })
  const { data: trades } = useQuery({
    queryKey: ['backtest-trades', runId],
    enabled: done,
    queryFn: () => api<Paginated<BacktestTrade>>(`/backtest-runs/${runId}/trades`),
  })

  const requestReport = useMutation({
    mutationFn: () =>
      api<InsightRequest>('/insights/performance-report', {
        method: 'POST',
        body: { backtest_run_id: runId },
      }),
    onSuccess: (req) => navigate(`/insights/${req.id}`),
  })

  const remove = useMutation({
    mutationFn: () => api(`/backtest-runs/${runId}`, { method: 'DELETE' }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['backtests'] })
      navigate('/backtests')
    },
  })

  if (!run) {
    return (
      <div className="mx-auto max-w-6xl space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  const points: SeriesPoint[] = (curve?.items ?? []).map((p) => ({
    ts: p.timestamp,
    value: Number(p.equity),
  }))

  return (
    <div className="mx-auto max-w-6xl">
      <Link
        to="/backtests"
        className="mb-3 inline-flex items-center gap-1 text-sm text-ink-300 hover:text-volt-300"
      >
        <ArrowLeft size={14} /> Backtests
      </Link>
      <PageHeader
        title={run.name}
        sub={`Submitted ${fmtDateTime(run.created_at)}`}
        actions={
          <>
            <StatusBadge status={run.status} />
            {done && (
              <button
                type="button"
                className={btnGhost}
                disabled={requestReport.isPending}
                onClick={() => requestReport.mutate()}
              >
                <BrainCircuit size={15} />
                {requestReport.isPending ? 'Requesting…' : 'AI report'}
              </button>
            )}
            <button
              type="button"
              className={btnBear}
              onClick={() => {
                if (confirm('Delete this backtest run?')) remove.mutate()
              }}
            >
              <Trash2 size={15} />
            </button>
          </>
        }
      />

      {run.status === 'failed' && (
        <div className="mb-6">
          <ErrorNote message={run.error_message ?? 'Backtest failed'} />
        </div>
      )}

      {(run.status === 'queued' || run.status === 'running') && (
        <div className="terminal-card mb-6 flex items-center gap-3 px-5 py-4">
          <span className="h-2.5 w-2.5 animate-pulse-dot rounded-full bg-volt-400" />
          <p className="text-sm text-ink-200">
            Engine is {run.status === 'queued' ? 'waiting for a worker' : 'crunching bars'} — this
            page refreshes automatically.
          </p>
        </div>
      )}

      {done && result && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 xl:grid-cols-6">
            <StatCard
              label="Total return"
              value={fmtPct(result.total_return)}
              accent={Number(result.total_return) >= 0 ? 'bull' : 'bear'}
            />
            <StatCard label="Sharpe" value={fmtNum(result.sharpe_ratio)} />
            <StatCard label="Sortino" value={fmtNum(result.sortino_ratio)} />
            <StatCard
              label="Max drawdown"
              value={fmtPct(result.max_drawdown)}
              accent="bear"
            />
            <StatCard label="Win rate" value={fmtPct(result.win_rate)} />
            <StatCard label="Trades" value={result.total_trades} />
          </div>

          {result.metrics?.long_trades != null && result.metrics?.short_trades != null && (
            <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
              <StatCard
                label="Long trades"
                value={
                  (result.metrics.long_trades as { count?: number })?.count ?? 0
                }
              />
              <StatCard
                label="Long win rate"
                value={fmtPct(
                  (result.metrics.long_trades as { win_rate?: string | null })?.win_rate,
                )}
              />
              <StatCard
                label="Short trades"
                value={
                  (result.metrics.short_trades as { count?: number })?.count ?? 0
                }
              />
              <StatCard
                label="Short win rate"
                value={fmtPct(
                  (result.metrics.short_trades as { win_rate?: string | null })?.win_rate,
                )}
              />
            </div>
          )}

          <div className="terminal-card mt-6 p-5">
            <p className="mb-3 font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Equity curve
            </p>
            <EquitySparkline data={points} height={320} />
          </div>

          <div className="terminal-card mt-6 overflow-x-auto">
            <div className="border-b border-ink-700 px-4 py-3">
              <p className="font-mono text-[11px] uppercase tracking-widest text-ink-300">
                Trade blotter ({trades?.total_count ?? 0})
              </p>
            </div>
            {(trades?.items ?? []).length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-ink-400">No trades recorded.</p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-ink-700 font-mono text-[11px] uppercase tracking-widest text-ink-300">
                    <th className="px-4 py-2.5 font-medium">Side</th>
                    <th className="px-4 py-2.5 font-medium">Qty</th>
                    <th className="px-4 py-2.5 font-medium">Entry</th>
                    <th className="px-4 py-2.5 font-medium">Exit</th>
                    <th className="px-4 py-2.5 font-medium">Entry time</th>
                    <th className="px-4 py-2.5 font-medium">Exit time</th>
                    <th className="px-4 py-2.5 text-right font-medium">PnL</th>
                  </tr>
                </thead>
                <tbody className="font-mono text-xs">
                  {(trades?.items ?? []).map((t) => (
                    <tr key={t.id} className="border-b border-ink-800 last:border-0">
                      <td className="px-4 py-2.5">
                        <span
                          className={`font-semibold uppercase ${
                            t.side === 'buy' ? 'text-bull-400' : 'text-bear-400'
                          }`}
                        >
                          {t.side}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-ink-200">{fmtNum(t.quantity, 0)}</td>
                      <td className="px-4 py-2.5 text-ink-200">{fmtMoney(t.entry_price)}</td>
                      <td className="px-4 py-2.5 text-ink-200">
                        {t.exit_price ? fmtMoney(t.exit_price) : '—'}
                      </td>
                      <td className="px-4 py-2.5 text-ink-300">{fmtDateTime(t.entry_time)}</td>
                      <td className="px-4 py-2.5 text-ink-300">{fmtDateTime(t.exit_time)}</td>
                      <td className={`px-4 py-2.5 text-right ${signClass(t.pnl)}`}>
                        {t.pnl ? fmtMoney(t.pnl) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  )
}
