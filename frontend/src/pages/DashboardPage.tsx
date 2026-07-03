import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowRight,
  CandlestickChart,
  FlaskConical,
  ScrollText,
  Wallet,
} from 'lucide-react'
import { api } from '../lib/api'
import { fmtDateTime, fmtMoney, fmtNum, signClass } from '../lib/format'
import ActivityFeed from '../components/ActivityFeed'
import { EquitySparkline, type SeriesPoint } from '../components/charts'
import { PageHeader, StatCard, StatusBadge, Skeleton } from '../components/ui'
import { useAuth } from '../lib/auth'
import type {
  BacktestResult,
  BacktestRun,
  EquityPoint,
  Order,
  Paginated,
  Portfolio,
  Strategy,
} from '../lib/types'

function useCounts() {
  const strategies = useQuery({
    queryKey: ['strategies', 'count'],
    queryFn: () => api<Paginated<Strategy>>('/strategies', { query: { limit: 1 } }),
  })
  const backtests = useQuery({
    queryKey: ['backtests', 'recent'],
    queryFn: () => api<Paginated<BacktestRun>>('/backtest-runs', { query: { limit: 6 } }),
    refetchInterval: 10_000,
  })
  const portfolios = useQuery({
    queryKey: ['portfolios', 'all'],
    queryFn: () => api<Paginated<Portfolio>>('/portfolios', { query: { limit: 100 } }),
  })
  const orders = useQuery({
    queryKey: ['orders', 'count'],
    queryFn: () => api<Paginated<Order>>('/orders', { query: { limit: 1 } }),
  })
  return { strategies, backtests, portfolios, orders }
}

function LatestBacktestChart({ runs }: { runs: BacktestRun[] }) {
  const completed = runs.find((r) => r.status === 'completed')
  const { data: curve } = useQuery({
    queryKey: ['equity-curve', completed?.id],
    enabled: !!completed,
    queryFn: () => api<Paginated<EquityPoint>>(`/backtest-runs/${completed!.id}/equity-curve`),
  })
  const { data: result } = useQuery({
    queryKey: ['backtest-result', completed?.id],
    enabled: !!completed,
    queryFn: () => api<BacktestResult>(`/backtest-runs/${completed!.id}/result`),
  })

  if (!completed) {
    return (
      <div className="terminal-card flex h-full min-h-[340px] flex-col items-center justify-center gap-2 p-6 text-center">
        <CandlestickChart size={32} className="text-ink-400" />
        <p className="font-medium text-ink-100">No completed backtests yet</p>
        <p className="text-sm text-ink-300">Run one to see the equity curve here.</p>
        <Link
          to="/backtests"
          className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-volt-400 hover:text-volt-300"
        >
          Launch a backtest <ArrowRight size={14} />
        </Link>
      </div>
    )
  }

  const points: SeriesPoint[] = (curve?.items ?? []).map((p) => ({
    ts: p.timestamp,
    value: Number(p.equity),
  }))

  return (
    <div className="terminal-card animate-rise p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-widest text-ink-300">
            Latest completed backtest
          </p>
          <Link
            to={`/backtests/${completed.id}`}
            className="text-base font-semibold text-white hover:text-volt-300"
          >
            {completed.name}
          </Link>
        </div>
        {result && (
          <div className="flex gap-5 font-mono text-sm">
            <span>
              <span className="text-ink-300">Return </span>
              <span className={signClass(result.total_return)}>
                {fmtNum(Number(result.total_return) * 100)}%
              </span>
            </span>
            <span>
              <span className="text-ink-300">Sharpe </span>
              <span className="text-ink-100">{fmtNum(result.sharpe_ratio)}</span>
            </span>
            <span>
              <span className="text-ink-300">Trades </span>
              <span className="text-ink-100">{result.total_trades}</span>
            </span>
          </div>
        )}
      </div>
      <EquitySparkline data={points} />
    </div>
  )
}

export default function DashboardPage() {
  const { user } = useAuth()
  const { strategies, backtests, portfolios, orders } = useCounts()

  const totalValue = (portfolios.data?.items ?? []).reduce(
    (acc, p) => acc + Number(p.cash_balance),
    0,
  )
  const runs = backtests.data?.items ?? []
  const running = runs.filter((r) => r.status === 'running' || r.status === 'queued').length

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        title={`Markets await, ${user?.display_name?.split(' ')[0] ?? 'trader'}.`}
        sub="Your quant command center — strategies, backtests, portfolios and risk at a glance."
      />

      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <StatCard
          label="Strategies"
          value={strategies.data?.total_count ?? <Skeleton className="h-7 w-12" />}
          icon={<FlaskConical size={16} />}
          sub={<Link to="/strategies" className="text-volt-400 hover:text-volt-300">Manage →</Link>}
        />
        <StatCard
          label="Backtests"
          value={backtests.data?.total_count ?? <Skeleton className="h-7 w-12" />}
          icon={<CandlestickChart size={16} />}
          accent={running > 0 ? 'volt' : 'neutral'}
          sub={running > 0 ? `${running} in flight` : 'All settled'}
        />
        <StatCard
          label="Portfolio cash"
          value={
            portfolios.isLoading ? <Skeleton className="h-7 w-20" /> : fmtMoney(totalValue)
          }
          icon={<Wallet size={16} />}
          accent="bull"
          sub={`${portfolios.data?.total_count ?? 0} portfolios`}
        />
        <StatCard
          label="Orders"
          value={orders.data?.total_count ?? <Skeleton className="h-7 w-12" />}
          icon={<ScrollText size={16} />}
          sub={<Link to="/orders" className="text-volt-400 hover:text-volt-300">Blotter →</Link>}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[2fr_1fr]">
        <LatestBacktestChart runs={runs} />

        <ActivityFeed />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_1fr]">
        <div className="terminal-card animate-rise p-5">
          <div className="mb-4 flex items-center justify-between">
            <p className="font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Recent runs
            </p>
            <Link
              to="/backtests"
              className="inline-flex items-center gap-1 text-xs font-medium text-volt-400 hover:text-volt-300"
            >
              View all <ArrowRight size={12} />
            </Link>
          </div>
          {backtests.isLoading ? (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : runs.length === 0 ? (
            <p className="py-8 text-center text-sm text-ink-300">
              No backtests yet — history starts here.
            </p>
          ) : (
            <ul className="space-y-2">
              {runs.map((r) => (
                <li key={r.id}>
                  <Link
                    to={`/backtests/${r.id}`}
                    className="flex items-center justify-between gap-2 rounded-lg border border-transparent px-3 py-2.5 transition hover:border-ink-600 hover:bg-ink-800/60"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-ink-100">{r.name}</p>
                      <p className="font-mono text-[11px] text-ink-400">
                        {fmtDateTime(r.created_at)}
                      </p>
                    </div>
                    <StatusBadge status={r.status} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="terminal-card animate-rise flex flex-col justify-center gap-4 p-6">
          <p className="font-mono text-[11px] uppercase tracking-widest text-ink-300">
            Quick launch
          </p>
          <div className="grid grid-cols-2 gap-3">
            {[
              {
                to: '/strategies',
                label: 'New strategy',
                desc: 'DSL or Python',
                hover: 'hover:border-volt-500/40',
              },
              {
                to: '/backtests',
                label: 'Run backtest',
                desc: 'Event engine',
                hover: 'hover:border-bull-500/40',
              },
              {
                to: '/optimizations',
                label: 'Optimize',
                desc: 'Grid search',
                hover: 'hover:border-gold-500/40',
              },
              {
                to: '/insights',
                label: 'AI report',
                desc: 'LLM insights',
                hover: 'hover:border-volt-500/40',
              },
            ].map((q) => (
              <Link
                key={q.to}
                to={q.to}
                className={`rounded-lg border border-ink-600 bg-ink-800/40 px-4 py-3 transition hover:bg-ink-800 ${q.hover}`}
              >
                <p className="text-sm font-semibold text-ink-100">{q.label}</p>
                <p className="font-mono text-[10px] text-ink-400">{q.desc}</p>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
