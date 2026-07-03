import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CandlestickChart, Plus, Rocket } from 'lucide-react'
import { api } from '../lib/api'
import { fmtDate, fmtDateTime } from '../lib/format'
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
  BacktestRun,
  Instrument,
  Paginated,
  Strategy,
  StrategyVersion,
} from '../lib/types'

function iso(d: string): string {
  return new Date(`${d}T00:00:00Z`).toISOString()
}

function NewBacktestModal({
  onClose,
  presetVersionId,
}: {
  onClose: () => void
  presetVersionId: string | null
}) {
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [strategyId, setStrategyId] = useState('')
  const [versionId, setVersionId] = useState(presetVersionId ?? '')
  const [instrumentIds, setInstrumentIds] = useState<string[]>([])
  const [startDate, setStartDate] = useState('2024-01-01')
  const [endDate, setEndDate] = useState('2024-12-31')
  const [capital, setCapital] = useState('100000')
  const [sizingModel, setSizingModel] = useState<'percent_equity' | 'fixed_quantity'>(
    'percent_equity',
  )
  const [sizingValue, setSizingValue] = useState('0.1')
  const [allowShort, setAllowShort] = useState(false)

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
    if (!presetVersionId && sortedVersions.length > 0) {
      setVersionId(sortedVersions[0].id)
    }
  }, [sortedVersions, presetVersionId])

  const submit = useMutation({
    mutationFn: () =>
      api<BacktestRun>('/backtest-runs', {
        method: 'POST',
        body: {
          strategy_version_id: versionId,
          name,
          config: {
            instrument_ids: instrumentIds,
            timeframe: '1d',
            start_date: iso(startDate),
            end_date: iso(endDate),
            initial_capital: capital,
            position_sizing: { model: sizingModel, value: Number(sizingValue) },
            allow_short: allowShort,
          },
        },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['backtests'] })
      onClose()
    },
  })

  const toggleInstrument = (id: string) => {
    setInstrumentIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    )
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    submit.mutate()
  }

  return (
    <Modal title="Launch backtest" onClose={onClose} wide>
      <form onSubmit={onSubmit} className="space-y-4">
        {submit.isError && (
          <ErrorNote
            message={submit.error instanceof Error ? submit.error.message : 'Submission failed'}
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
              placeholder="Golden cross — 2024 full year"
            />
          </div>
          <div>
            <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Strategy
            </label>
            <select
              className={inputCls}
              value={strategyId}
              onChange={(e) => setStrategyId(e.target.value)}
              required={!presetVersionId}
            >
              <option value="">
                {presetVersionId ? 'Preselected version' : 'Select strategy…'}
              </option>
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
              className={inputCls}
              value={versionId}
              onChange={(e) => setVersionId(e.target.value)}
              required
              disabled={!strategyId && !!presetVersionId}
            >
              {presetVersionId && <option value={presetVersionId}>Selected version</option>}
              {sortedVersions.map((v) => (
                <option key={v.id} value={v.id}>
                  v{v.version} ({v.status})
                </option>
              ))}
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
          <div>
            <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Initial capital
            </label>
            <input
              required
              inputMode="decimal"
              className={inputCls}
              value={capital}
              onChange={(e) => setCapital(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Position sizing
            </label>
            <div className="flex gap-2">
              <select
                className={inputCls}
                value={sizingModel}
                onChange={(e) =>
                  setSizingModel(e.target.value as 'percent_equity' | 'fixed_quantity')
                }
              >
                <option value="percent_equity">% equity</option>
                <option value="fixed_quantity">Fixed qty</option>
              </select>
              <input
                required
                inputMode="decimal"
                className={inputCls}
                value={sizingValue}
                onChange={(e) => setSizingValue(e.target.value)}
              />
            </div>
          </div>
          <div className="sm:col-span-2">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-ink-200">
              <input
                type="checkbox"
                checked={allowShort}
                onChange={(e) => setAllowShort(e.target.checked)}
                className="rounded border-ink-500"
              />
              Allow short selling (SELL opens short when flat; uses Python engine)
            </label>
          </div>
        </div>

        <div>
          <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
            Instruments ({instrumentIds.length} selected)
          </label>
          <div className="flex max-h-36 flex-wrap gap-2 overflow-y-auto rounded-lg border border-ink-600 bg-ink-900 p-3">
            {(instruments?.items ?? []).length === 0 && (
              <p className="text-sm text-ink-400">
                No instruments found — ingest market data first.
              </p>
            )}
            {(instruments?.items ?? []).map((inst) => {
              const on = instrumentIds.includes(inst.id)
              return (
                <button
                  key={inst.id}
                  type="button"
                  onClick={() => toggleInstrument(inst.id)}
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
          <Rocket size={16} />
          {submit.isPending ? 'Queuing…' : 'Queue backtest'}
        </button>
      </form>
    </Modal>
  )
}

export default function BacktestsPage() {
  const [params, setParams] = useSearchParams()
  const presetVersionId = params.get('strategy_version_id')
  const [showCreate, setShowCreate] = useState(!!presetVersionId)

  const { data, isLoading } = useQuery({
    queryKey: ['backtests', 'list'],
    queryFn: () => api<Paginated<BacktestRun>>('/backtest-runs', { query: { limit: 100 } }),
    refetchInterval: 8_000,
  })

  const items = data?.items ?? []

  const close = () => {
    setShowCreate(false)
    if (presetVersionId) setParams({}, { replace: true })
  }

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        title="Backtests"
        sub="Replay your strategies against history — event-driven, C++ accelerated."
        actions={
          <button type="button" className={btnPrimary} onClick={() => setShowCreate(true)}>
            <Plus size={16} /> New backtest
          </button>
        }
      />

      {isLoading ? (
        <Skeleton className="h-80 w-full" />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<CandlestickChart size={24} />}
          title="No backtests yet"
          hint="Queue your first run and watch the equity curve materialize."
          action={
            <button type="button" className={btnPrimary} onClick={() => setShowCreate(true)}>
              <Plus size={16} /> Launch backtest
            </button>
          }
        />
      ) : (
        <div className="terminal-card overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-ink-700 font-mono text-[11px] uppercase tracking-widest text-ink-300">
                <th className="px-4 py-3 font-medium">Run</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Window</th>
                <th className="px-4 py-3 font-medium">Submitted</th>
                <th className="px-4 py-3 font-medium">Completed</th>
              </tr>
            </thead>
            <tbody>
              {items.map((r) => (
                <tr
                  key={r.id}
                  className="border-b border-ink-800 transition last:border-0 hover:bg-ink-800/50"
                >
                  <td className="px-4 py-3">
                    <Link
                      to={`/backtests/${r.id}`}
                      className="font-medium text-ink-100 hover:text-volt-300"
                    >
                      {r.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-ink-300">
                    {fmtDate(r.config.start_date)} → {fmtDate(r.config.end_date)}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-ink-300">
                    {fmtDateTime(r.created_at)}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-ink-300">
                    {fmtDateTime(r.completed_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && <NewBacktestModal onClose={close} presetVersionId={presetVersionId} />}
    </div>
  )
}
