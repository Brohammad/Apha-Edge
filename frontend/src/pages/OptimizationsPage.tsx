import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, SlidersHorizontal, Zap } from 'lucide-react'
import { api } from '../lib/api'
import { fmtDateTime } from '../lib/format'
import Modal from '../components/Modal'
import {
  EmptyState,
  ErrorNote,
  PageHeader,
  Skeleton,
  StatusBadge,
  btnPrimary,
  inputCls,
} from '../components/ui'
import type {
  Instrument,
  OptimizationRun,
  Paginated,
  Strategy,
  StrategyVersion,
} from '../lib/types'

const PARAM_SPACE_PLACEHOLDER = `{
  "fast_period": [5, 10, 15],
  "slow_period": [20, 30, 50]
}`

function NewOptimizationModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [strategyId, setStrategyId] = useState('')
  const [versionId, setVersionId] = useState('')
  const [method, setMethod] = useState<'grid_search' | 'walk_forward'>('grid_search')
  const [objective, setObjective] = useState('sharpe_ratio')
  const [paramSpace, setParamSpace] = useState(PARAM_SPACE_PLACEHOLDER)
  const [instrumentIds, setInstrumentIds] = useState<string[]>([])
  const [startDate, setStartDate] = useState('2024-01-01')
  const [endDate, setEndDate] = useState('2024-12-31')
  const [jsonError, setJsonError] = useState<string | null>(null)

  const { data: strategies } = useQuery({
    queryKey: ['strategies', 'list'],
    queryFn: () =>
      api<Paginated<Strategy>>('/strategies', { query: { limit: 100, active_only: false } }),
  })
  const { data: versions } = useQuery({
    queryKey: ['strategy-versions', strategyId],
    enabled: !!strategyId,
    queryFn: () => api<Paginated<StrategyVersion>>(`/strategies/${strategyId}/versions`),
  })
  const { data: instruments } = useQuery({
    queryKey: ['instruments', 'all'],
    queryFn: () => api<Paginated<Instrument>>('/instruments', { query: { limit: 200 } }),
  })

  const sortedVersions = useMemo(
    () => [...(versions?.items ?? [])].sort((a, b) => b.version - a.version),
    [versions],
  )
  useEffect(() => {
    if (sortedVersions.length > 0) setVersionId(sortedVersions[0].id)
  }, [sortedVersions])

  const submit = useMutation({
    mutationFn: (space: Record<string, unknown[]>) =>
      api<OptimizationRun>('/optimization-runs', {
        method: 'POST',
        body: {
          strategy_version_id: versionId,
          name,
          method,
          objective,
          parameter_space: space,
          backtest_config: {
            instrument_ids: instrumentIds,
            timeframe: '1d',
            start_date: new Date(`${startDate}T00:00:00Z`).toISOString(),
            end_date: new Date(`${endDate}T00:00:00Z`).toISOString(),
          },
          walk_forward_config:
            method === 'walk_forward' ? { train_days: 60, test_days: 20 } : null,
        },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['optimizations'] })
      onClose()
    },
  })

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    setJsonError(null)
    let space: Record<string, unknown[]>
    try {
      space = JSON.parse(paramSpace)
    } catch {
      setJsonError('Parameter space must be valid JSON')
      return
    }
    submit.mutate(space)
  }

  return (
    <Modal title="New optimization" onClose={onClose} wide>
      <form onSubmit={onSubmit} className="space-y-4">
        {(submit.isError || jsonError) && (
          <ErrorNote
            message={
              jsonError ??
              (submit.error instanceof Error ? submit.error.message : 'Submission failed')
            }
          />
        )}
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Run name
            </label>
            <input
              required
              className={inputCls}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Golden cross sweep"
            />
          </div>
          <div>
            <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Strategy
            </label>
            <select
              required
              className={inputCls}
              value={strategyId}
              onChange={(e) => setStrategyId(e.target.value)}
            >
              <option value="">Select strategy…</option>
              {(strategies?.items ?? []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Version
            </label>
            <select
              required
              className={inputCls}
              value={versionId}
              onChange={(e) => setVersionId(e.target.value)}
            >
              {sortedVersions.map((v) => (
                <option key={v.id} value={v.id}>
                  v{v.version} ({v.status})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Method
            </label>
            <select
              className={inputCls}
              value={method}
              onChange={(e) => setMethod(e.target.value as typeof method)}
            >
              <option value="grid_search">Grid search</option>
              <option value="walk_forward">Walk-forward</option>
            </select>
          </div>
          <div>
            <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Objective
            </label>
            <select
              className={inputCls}
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
            >
              <option value="sharpe_ratio">Sharpe ratio</option>
              <option value="total_return">Total return</option>
              <option value="sortino_ratio">Sortino ratio</option>
              <option value="max_drawdown">Max drawdown</option>
            </select>
          </div>
          <div>
            <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Start date
            </label>
            <input
              type="date"
              required
              className={inputCls}
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
              End date
            </label>
            <input
              type="date"
              required
              className={inputCls}
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
        </div>

        <div>
          <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
            Parameter space (JSON — key → list of values)
          </label>
          <textarea
            spellCheck={false}
            className={`${inputCls} min-h-28 resize-y font-mono text-xs`}
            value={paramSpace}
            onChange={(e) => setParamSpace(e.target.value)}
          />
        </div>

        <div>
          <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
            Instruments ({instrumentIds.length} selected)
          </label>
          <div className="flex max-h-32 flex-wrap gap-2 overflow-y-auto rounded-lg border border-ink-600 bg-ink-900 p-3">
            {(instruments?.items ?? []).map((inst) => {
              const on = instrumentIds.includes(inst.id)
              return (
                <button
                  key={inst.id}
                  type="button"
                  onClick={() =>
                    setInstrumentIds((prev) =>
                      on ? prev.filter((x) => x !== inst.id) : [...prev, inst.id],
                    )
                  }
                  className={`rounded-md border px-2.5 py-1 font-mono text-xs font-semibold transition ${
                    on
                      ? 'border-bull-500/60 bg-bull-500/15 text-bull-300'
                      : 'border-ink-600 text-ink-300 hover:border-ink-400'
                  }`}
                >
                  {inst.symbol}
                </button>
              )
            })}
          </div>
        </div>

        <button
          type="submit"
          disabled={submit.isPending || instrumentIds.length === 0 || !versionId}
          className={`${btnPrimary} w-full`}
        >
          <Zap size={16} />
          {submit.isPending ? 'Queuing…' : 'Start optimization'}
        </button>
      </form>
    </Modal>
  )
}

export default function OptimizationsPage() {
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = useQuery({
    queryKey: ['optimizations', 'list'],
    queryFn: () => api<Paginated<OptimizationRun>>('/optimization-runs', { query: { limit: 100 } }),
    refetchInterval: 8_000,
  })

  const items = data?.items ?? []

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        title="Optimizer"
        sub="Sweep the parameter space — grid search and walk-forward validation."
        actions={
          <button type="button" className={btnPrimary} onClick={() => setShowCreate(true)}>
            <Plus size={16} /> New optimization
          </button>
        }
      />

      {isLoading ? (
        <Skeleton className="h-80 w-full" />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<SlidersHorizontal size={24} />}
          title="No optimizations yet"
          hint="Let the machine hunt for parameters while you drink your coffee."
          action={
            <button type="button" className={btnPrimary} onClick={() => setShowCreate(true)}>
              <Plus size={16} /> Start sweeping
            </button>
          }
        />
      ) : (
        <div className="terminal-card overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-ink-700 font-mono text-[11px] uppercase tracking-widest text-ink-300">
                <th className="px-4 py-3 font-medium">Run</th>
                <th className="px-4 py-3 font-medium">Method</th>
                <th className="px-4 py-3 font-medium">Objective</th>
                <th className="px-4 py-3 font-medium">Progress</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {items.map((r) => {
                const pct = r.total_trials > 0 ? (r.completed_trials / r.total_trials) * 100 : 0
                return (
                  <tr
                    key={r.id}
                    className="border-b border-ink-800 transition last:border-0 hover:bg-ink-800/50"
                  >
                    <td className="px-4 py-3">
                      <Link
                        to={`/optimizations/${r.id}`}
                        className="font-medium text-ink-100 hover:text-volt-300"
                      >
                        {r.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-ink-300">
                      {r.method.replace('_', ' ')}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-ink-300">
                      {r.objective.replace('_', ' ')}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-24 overflow-hidden rounded-full bg-ink-700">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-volt-500 to-bull-500 transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="font-mono text-[11px] text-ink-300">
                          {r.completed_trials}/{r.total_trials}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-ink-300">
                      {fmtDateTime(r.created_at)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && <NewOptimizationModal onClose={() => setShowCreate(false)} />}
    </div>
  )
}
