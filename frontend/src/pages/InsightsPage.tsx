import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BrainCircuit, Plus, Sparkles } from 'lucide-react'
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
  BacktestRun,
  InsightRequest,
  Instrument,
  Paginated,
  Strategy,
} from '../lib/types'

const TYPE_LABELS: Record<string, string> = {
  strategy_explanation: 'Strategy explanation',
  performance_report: 'Performance report',
  risk_interpretation: 'Risk interpretation',
  trade_summary: 'Trade summary',
  company_research: 'Company research',
}

function NewInsightModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient()
  const [kind, setKind] = useState<'strategy' | 'backtest' | 'research'>('strategy')
  const [strategyId, setStrategyId] = useState('')
  const [backtestId, setBacktestId] = useState('')
  const [instrumentId, setInstrumentId] = useState('')

  const { data: strategies } = useQuery({
    queryKey: ['strategies', 'list'],
    queryFn: () =>
      api<Paginated<Strategy>>('/strategies', { query: { limit: 100, active_only: false } }),
  })
  const { data: backtests } = useQuery({
    queryKey: ['backtests', 'completed'],
    queryFn: () => api<Paginated<BacktestRun>>('/backtest-runs', { query: { limit: 100 } }),
  })
  const { data: instruments } = useQuery({
    queryKey: ['instruments', 'research'],
    queryFn: () => api<Paginated<Instrument>>('/instruments', { query: { limit: 100 } }),
  })
  const completedRuns = (backtests?.items ?? []).filter((r) => r.status === 'completed')

  const submit = useMutation({
    mutationFn: () => {
      if (kind === 'strategy') {
        return api<InsightRequest>('/insights/strategy-explain', {
          method: 'POST',
          body: { strategy_id: strategyId },
        })
      }
      if (kind === 'backtest') {
        return api<InsightRequest>('/insights/performance-report', {
          method: 'POST',
          body: { backtest_run_id: backtestId },
        })
      }
      return api<InsightRequest>('/insights', {
        method: 'POST',
        body: {
          insight_type: 'company_research',
          source_type: 'instrument',
          source_id: instrumentId,
        },
      })
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['insights'] })
      onClose()
    },
  })

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    submit.mutate()
  }

  return (
    <Modal title="Request AI insight" onClose={onClose}>
      <form onSubmit={onSubmit} className="space-y-4">
        {submit.isError && (
          <ErrorNote
            message={submit.error instanceof Error ? submit.error.message : 'Request failed'}
          />
        )}
        <div className="grid grid-cols-3 gap-2">
          <button
            type="button"
            onClick={() => setKind('strategy')}
            className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${
              kind === 'strategy'
                ? 'border-volt-500 bg-volt-500/10 text-volt-300'
                : 'border-ink-600 text-ink-300 hover:border-ink-400'
            }`}
          >
            Explain strategy
          </button>
          <button
            type="button"
            onClick={() => setKind('backtest')}
            className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${
              kind === 'backtest'
                ? 'border-volt-500 bg-volt-500/10 text-volt-300'
                : 'border-ink-600 text-ink-300 hover:border-ink-400'
            }`}
          >
            Performance report
          </button>
          <button
            type="button"
            onClick={() => setKind('research')}
            className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${
              kind === 'research'
                ? 'border-volt-500 bg-volt-500/10 text-volt-300'
                : 'border-ink-600 text-ink-300 hover:border-ink-400'
            }`}
          >
            Company research
          </button>
        </div>

        {kind === 'strategy' ? (
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
        ) : kind === 'backtest' ? (
          <div>
            <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Completed backtest
            </label>
            <select
              required
              className={inputCls}
              value={backtestId}
              onChange={(e) => setBacktestId(e.target.value)}
            >
              <option value="">Select backtest…</option>
              {completedRuns.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </div>
        ) : (
          <div>
            <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Instrument
            </label>
            <select
              required
              className={inputCls}
              value={instrumentId}
              onChange={(e) => setInstrumentId(e.target.value)}
            >
              <option value="">Select symbol…</option>
              {(instruments?.items ?? []).map((i) => (
                <option key={i.id} value={i.id}>
                  {i.symbol} — {i.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <button type="submit" disabled={submit.isPending} className={`${btnPrimary} w-full`}>
          <Sparkles size={15} />
          {submit.isPending ? 'Requesting…' : 'Generate insight'}
        </button>
      </form>
    </Modal>
  )
}

export default function InsightsPage() {
  const [showCreate, setShowCreate] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['insights', 'list'],
    queryFn: () => api<Paginated<InsightRequest>>('/insights', { query: { limit: 100 } }),
    refetchInterval: 8_000,
  })

  const items = data?.items ?? []

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        title="AI Insights"
        sub="OpenAI-powered strategy explanations, performance reports and risk narratives."
        actions={
          <button type="button" className={btnPrimary} onClick={() => setShowCreate(true)}>
            <Plus size={16} /> Request insight
          </button>
        }
      />

      {isLoading ? (
        <Skeleton className="h-80 w-full" />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<BrainCircuit size={24} />}
          title="No insights yet"
          hint="Ask the AI to explain a strategy or narrate a backtest's performance."
          action={
            <button type="button" className={btnPrimary} onClick={() => setShowCreate(true)}>
              <Plus size={16} /> Request insight
            </button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {items.map((r) => (
            <Link
              key={r.id}
              to={`/insights/${r.id}`}
              className="terminal-card animate-rise group flex items-center justify-between gap-3 p-5 transition hover:border-volt-500/50"
            >
              <div className="min-w-0">
                <p className="font-semibold text-white group-hover:text-volt-300">
                  {TYPE_LABELS[r.insight_type] ?? r.insight_type}
                </p>
                <p className="mt-1 font-mono text-[11px] text-ink-400">
                  {r.source_type} · {fmtDateTime(r.created_at)}
                </p>
              </div>
              <StatusBadge status={r.status} />
            </Link>
          ))}
        </div>
      )}

      {showCreate && <NewInsightModal onClose={() => setShowCreate(false)} />}
    </div>
  )
}
