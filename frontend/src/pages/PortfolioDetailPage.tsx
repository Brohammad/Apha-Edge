import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Download, Gauge, ShieldAlert } from 'lucide-react'
import { api } from '../lib/api'
import { fmtDateTime, fmtMoney, fmtNum, fmtPct, signClass } from '../lib/format'
import Modal from '../components/Modal'
import {
  ErrorNote,
  PageHeader,
  Skeleton,
  StatCard,
  btnGhost,
  btnPrimary,
  inputCls,
} from '../components/ui'
import type {
  BacktestRun,
  Holding,
  Instrument,
  Paginated,
  Portfolio,
  PortfolioPerformance,
  RiskSnapshot,
} from '../lib/types'

function SyncModal({ portfolioId, onClose }: { portfolioId: string; onClose: () => void }) {
  const qc = useQueryClient()
  const [runId, setRunId] = useState('')

  const { data: runs } = useQuery({
    queryKey: ['backtests', 'completed'],
    queryFn: () => api<Paginated<BacktestRun>>('/backtest-runs', { query: { limit: 100 } }),
  })
  const completed = (runs?.items ?? []).filter((r) => r.status === 'completed')

  const sync = useMutation({
    mutationFn: () =>
      api(`/portfolios/${portfolioId}/sync-from-backtest`, {
        method: 'POST',
        body: { backtest_run_id: runId },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['portfolio', portfolioId] })
      void qc.invalidateQueries({ queryKey: ['holdings', portfolioId] })
      void qc.invalidateQueries({ queryKey: ['performance', portfolioId] })
      onClose()
    },
  })

  return (
    <Modal title="Sync holdings from backtest" onClose={onClose}>
      <div className="space-y-4">
        {sync.isError && (
          <ErrorNote message={sync.error instanceof Error ? sync.error.message : 'Sync failed'} />
        )}
        <p className="text-sm text-ink-300">
          Import the final positions of a completed backtest into this portfolio.
        </p>
        <select className={inputCls} value={runId} onChange={(e) => setRunId(e.target.value)}>
          <option value="">Select a completed backtest…</option>
          {completed.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          disabled={!runId || sync.isPending}
          className={`${btnPrimary} w-full`}
          onClick={() => sync.mutate()}
        >
          <Download size={15} />
          {sync.isPending ? 'Syncing…' : 'Sync holdings'}
        </button>
      </div>
    </Modal>
  )
}

function RiskPanel({ portfolioId }: { portfolioId: string }) {
  const qc = useQueryClient()

  const { data: latest, isError } = useQuery({
    queryKey: ['risk-latest', portfolioId],
    queryFn: () => api<RiskSnapshot>(`/portfolios/${portfolioId}/risk/snapshots/latest`),
    retry: false,
  })

  const compute = useMutation({
    mutationFn: () =>
      api<RiskSnapshot>(`/portfolios/${portfolioId}/risk/compute`, { method: 'POST' }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['risk-latest', portfolioId] })
    },
  })

  const snap = compute.data ?? (isError ? null : latest)

  return (
    <div className="terminal-card p-5">
      <div className="mb-4 flex items-center justify-between">
        <p className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-ink-300">
          <Gauge size={13} /> Risk analytics
        </p>
        <button
          type="button"
          className={btnGhost}
          disabled={compute.isPending}
          onClick={() => compute.mutate()}
        >
          {compute.isPending ? 'Computing…' : 'Compute snapshot'}
        </button>
      </div>

      {compute.isError && (
        <ErrorNote
          message={compute.error instanceof Error ? compute.error.message : 'Compute failed'}
        />
      )}

      {!snap ? (
        <p className="py-6 text-center text-sm text-ink-400">
          No risk snapshot yet — compute one to see VaR, Sharpe, beta and more.
        </p>
      ) : (
        <>
          <p className="mb-3 font-mono text-[11px] text-ink-400">
            As of {fmtDateTime(snap.snapshot_at)}
          </p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="VaR 95%" value={fmtPct(snap.var_95)} accent="bear" />
            <StatCard label="VaR 99%" value={fmtPct(snap.var_99)} accent="bear" />
            <StatCard label="Sharpe" value={fmtNum(snap.sharpe_ratio)} />
            <StatCard label="Sortino" value={fmtNum(snap.sortino_ratio)} />
            <StatCard label="Volatility" value={fmtPct(snap.volatility)} />
            <StatCard label="Max drawdown" value={fmtPct(snap.max_drawdown)} accent="bear" />
            <StatCard label="Beta" value={fmtNum(snap.beta)} />
            <StatCard label="Alpha" value={fmtNum(snap.alpha, 4)} accent="bull" />
          </div>

          {snap.violations.length > 0 && (
            <div className="mt-4 rounded-lg border border-bear-500/40 bg-bear-500/10 p-4">
              <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-bear-300">
                <ShieldAlert size={15} /> Limit violations
              </p>
              <ul className="space-y-1 font-mono text-xs text-bear-300">
                {snap.violations.map((v, i) => (
                  <li key={i}>• {v.message}</li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default function PortfolioDetailPage() {
  const { portfolioId } = useParams<{ portfolioId: string }>()
  const [showSync, setShowSync] = useState(false)

  const { data: portfolio } = useQuery({
    queryKey: ['portfolio', portfolioId],
    queryFn: () => api<Portfolio>(`/portfolios/${portfolioId}`),
  })
  const { data: holdings } = useQuery({
    queryKey: ['holdings', portfolioId],
    queryFn: () => api<Paginated<Holding>>(`/portfolios/${portfolioId}/holdings`),
  })
  const { data: perf } = useQuery({
    queryKey: ['performance', portfolioId],
    queryFn: () => api<PortfolioPerformance>(`/portfolios/${portfolioId}/performance`),
  })
  const { data: instruments } = useQuery({
    queryKey: ['instruments', 'all'],
    queryFn: () => api<Paginated<Instrument>>('/instruments', { query: { limit: 200 } }),
  })

  const symbolById = useMemo(() => {
    const m = new Map<string, string>()
    for (const i of instruments?.items ?? []) m.set(i.id, i.symbol)
    return m
  }, [instruments])

  if (!portfolio) {
    return (
      <div className="mx-auto max-w-6xl space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  const items = holdings?.items ?? []

  return (
    <div className="mx-auto max-w-6xl">
      <Link
        to="/portfolios"
        className="mb-3 inline-flex items-center gap-1 text-sm text-ink-300 hover:text-volt-300"
      >
        <ArrowLeft size={14} /> Portfolios
      </Link>
      <PageHeader
        title={portfolio.name}
        sub={portfolio.is_paper ? 'Paper trading book' : 'Live book'}
        actions={
          <button type="button" className={btnGhost} onClick={() => setShowSync(true)}>
            <Download size={15} /> Sync from backtest
          </button>
        }
      />

      {perf && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          <StatCard
            label="Total value"
            value={fmtMoney(perf.total_value, portfolio.base_currency)}
            accent="volt"
          />
          <StatCard label="Cash" value={fmtMoney(perf.cash_balance, portfolio.base_currency)} />
          <StatCard
            label="Invested"
            value={fmtMoney(perf.invested_value, portfolio.base_currency)}
          />
          <StatCard
            label="Total return"
            value={fmtPct(perf.total_return)}
            accent={Number(perf.total_return) >= 0 ? 'bull' : 'bear'}
          />
          <StatCard label="Holdings" value={perf.holdings_count} />
        </div>
      )}

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <div className="terminal-card overflow-x-auto">
          <div className="border-b border-ink-700 px-4 py-3">
            <p className="font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Holdings
            </p>
          </div>
          {items.length === 0 ? (
            <p className="px-4 py-10 text-center text-sm text-ink-400">
              Empty book — sync a backtest or execute orders to build positions.
            </p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-ink-700 font-mono text-[11px] uppercase tracking-widest text-ink-300">
                  <th className="px-4 py-2.5 font-medium">Symbol</th>
                  <th className="px-4 py-2.5 text-right font-medium">Qty</th>
                  <th className="px-4 py-2.5 text-right font-medium">Avg cost</th>
                  <th className="px-4 py-2.5 text-right font-medium">Price</th>
                  <th className="px-4 py-2.5 text-right font-medium">Value</th>
                  <th className="px-4 py-2.5 text-right font-medium">Unrealized</th>
                </tr>
              </thead>
              <tbody className="font-mono text-xs">
                {items.map((h) => {
                  const unrealized =
                    (Number(h.current_price) - Number(h.avg_cost)) * Number(h.quantity)
                  return (
                    <tr key={h.id} className="border-b border-ink-800 last:border-0">
                      <td className="px-4 py-2.5 font-semibold text-ink-100">
                        {symbolById.get(h.instrument_id) ?? h.instrument_id.slice(0, 8)}
                      </td>
                      <td className="px-4 py-2.5 text-right text-ink-200">
                        {fmtNum(h.quantity, 0)}
                      </td>
                      <td className="px-4 py-2.5 text-right text-ink-200">
                        {fmtMoney(h.avg_cost)}
                      </td>
                      <td className="px-4 py-2.5 text-right text-ink-200">
                        {fmtMoney(h.current_price)}
                      </td>
                      <td className="px-4 py-2.5 text-right text-ink-100">
                        {fmtMoney(h.market_value)}
                      </td>
                      <td className={`px-4 py-2.5 text-right ${signClass(unrealized)}`}>
                        {fmtMoney(unrealized)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>

        <RiskPanel portfolioId={portfolio.id} />
      </div>

      {showSync && <SyncModal portfolioId={portfolio.id} onClose={() => setShowSync(false)} />}
    </div>
  )
}
