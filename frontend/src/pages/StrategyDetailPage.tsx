import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  GitBranch,
  Play,
  Save,
  ShieldCheck,
  Trash2,
  XCircle,
} from 'lucide-react'
import { api } from '../lib/api'
import { fmtDateTime } from '../lib/format'
import {
  ErrorNote,
  PageHeader,
  Skeleton,
  StatusBadge,
  btnBear,
  btnGhost,
  btnPrimary,
} from '../components/ui'
import type {
  Paginated,
  Strategy,
  StrategyVersion,
  ValidationResult,
} from '../lib/types'

export default function StrategyDetailPage() {
  const { strategyId } = useParams<{ strategyId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: strategy, isLoading } = useQuery({
    queryKey: ['strategy', strategyId],
    queryFn: () => api<Strategy>(`/strategies/${strategyId}`),
  })

  const { data: versions } = useQuery({
    queryKey: ['strategy-versions', strategyId],
    queryFn: () =>
      api<Paginated<StrategyVersion>>(`/strategies/${strategyId}/versions`),
  })

  const sorted = useMemo(
    () => [...(versions?.items ?? [])].sort((a, b) => b.version - a.version),
    [versions],
  )
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const selected = sorted.find((v) => v.id === selectedId) ?? sorted[0] ?? null

  const [code, setCode] = useState('')
  const [dirty, setDirty] = useState(false)
  const [validation, setValidation] = useState<ValidationResult | null>(null)

  useEffect(() => {
    setCode(selected?.source_code ?? '')
    setDirty(false)
    setValidation(null)
  }, [selected?.id, selected?.source_code])

  const saveVersion = useMutation({
    mutationFn: () =>
      api<StrategyVersion>(`/strategies/${strategyId}/versions`, {
        method: 'POST',
        body: { source_code: code },
      }),
    onSuccess: (v) => {
      void qc.invalidateQueries({ queryKey: ['strategy-versions', strategyId] })
      setSelectedId(v.id)
      setDirty(false)
    },
  })

  const validate = useMutation({
    mutationFn: (versionId: string) =>
      api<ValidationResult>(`/strategies/${strategyId}/versions/${versionId}/validate`, {
        method: 'POST',
      }),
    onSuccess: (res) => {
      setValidation(res)
      void qc.invalidateQueries({ queryKey: ['strategy-versions', strategyId] })
    },
  })

  const remove = useMutation({
    mutationFn: () => api(`/strategies/${strategyId}`, { method: 'DELETE' }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['strategies'] })
      navigate('/strategies')
    },
  })

  if (isLoading || !strategy) {
    return (
      <div className="mx-auto max-w-6xl space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  const lineCount = code.split('\n').length

  return (
    <div className="mx-auto max-w-6xl">
      <Link
        to="/strategies"
        className="mb-3 inline-flex items-center gap-1 text-sm text-ink-300 hover:text-volt-300"
      >
        <ArrowLeft size={14} /> Strategies
      </Link>
      <PageHeader
        title={strategy.name}
        sub={strategy.description ?? undefined}
        actions={
          <>
            <Link
              to={`/backtests?strategy_version_id=${selected?.id ?? ''}`}
              className={btnPrimary}
              aria-disabled={!selected}
            >
              <Play size={15} /> Backtest
            </Link>
            <button
              type="button"
              className={btnBear}
              onClick={() => {
                if (confirm(`Delete strategy "${strategy.name}"? This cannot be undone.`)) {
                  remove.mutate()
                }
              }}
            >
              <Trash2 size={15} />
            </button>
          </>
        }
      />

      <div className="grid gap-5 lg:grid-cols-[260px_1fr]">
        <div className="terminal-card h-fit p-4">
          <p className="mb-3 flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-ink-300">
            <GitBranch size={13} /> Versions
          </p>
          {sorted.length === 0 ? (
            <p className="text-sm text-ink-400">No versions yet — write code and save.</p>
          ) : (
            <ul className="space-y-1.5">
              {sorted.map((v) => (
                <li key={v.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(v.id)}
                    className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left transition ${
                      selected?.id === v.id
                        ? 'border-volt-500/50 bg-volt-500/10'
                        : 'border-transparent hover:border-ink-600 hover:bg-ink-800/60'
                    }`}
                  >
                    <div>
                      <p className="font-mono text-sm font-semibold text-ink-100">
                        v{v.version}
                      </p>
                      <p className="font-mono text-[10px] text-ink-400">
                        {fmtDateTime(v.created_at)}
                      </p>
                    </div>
                    <div className="flex items-center gap-1">
                      <StatusBadge status={v.status} />
                      <ChevronRight size={14} className="text-ink-400" />
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="space-y-4">
          <div className="terminal-card overflow-hidden">
            <div className="flex items-center justify-between border-b border-ink-700 bg-ink-900/60 px-4 py-2">
              <p className="font-mono text-xs text-ink-300">
                {strategy.strategy_type === 'dsl' ? 'strategy.yaml' : 'strategy.py'}
                {dirty && <span className="ml-2 text-gold-400">● unsaved</span>}
              </p>
              <p className="font-mono text-[11px] text-ink-400">{lineCount} lines</p>
            </div>
            <textarea
              spellCheck={false}
              className="block h-96 w-full resize-y bg-ink-950/70 p-4 font-mono text-[13px] leading-relaxed text-ink-100 outline-none"
              value={code}
              onChange={(e) => {
                setCode(e.target.value)
                setDirty(true)
              }}
              placeholder={
                strategy.strategy_type === 'dsl'
                  ? 'name: my-strategy\nparameters:\n  fast: 10\nsignals:\n  - when: crossover(sma(fast), sma(30))\n    then: BUY'
                  : 'class MyStrategy(StrategyBase):\n    ...'
              }
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className={btnPrimary}
              disabled={saveVersion.isPending || code.trim().length === 0 || !dirty}
              onClick={() => saveVersion.mutate()}
            >
              <Save size={15} />
              {saveVersion.isPending ? 'Saving…' : `Save as v${(sorted[0]?.version ?? 0) + 1}`}
            </button>
            <button
              type="button"
              className={btnGhost}
              disabled={!selected || validate.isPending || dirty}
              title={dirty ? 'Save the version first' : undefined}
              onClick={() => selected && validate.mutate(selected.id)}
            >
              <ShieldCheck size={15} />
              {validate.isPending ? 'Validating…' : 'Validate'}
            </button>
          </div>

          {saveVersion.isError && (
            <ErrorNote
              message={
                saveVersion.error instanceof Error ? saveVersion.error.message : 'Save failed'
              }
            />
          )}
          {validate.isError && (
            <ErrorNote
              message={
                validate.error instanceof Error ? validate.error.message : 'Validation failed'
              }
            />
          )}
          {validation &&
            (validation.errors.length === 0 ? (
              <div className="flex items-center gap-2 rounded-lg border border-bull-500/40 bg-bull-500/10 px-4 py-3 text-sm text-bull-300">
                <CheckCircle2 size={16} />
                Validated — compiled hash{' '}
                <code className="font-mono text-xs">{validation.compiled_hash.slice(0, 12)}</code>
              </div>
            ) : (
              <div className="rounded-lg border border-bear-500/40 bg-bear-500/10 px-4 py-3 text-sm text-bear-300">
                <p className="mb-1 flex items-center gap-2 font-semibold">
                  <XCircle size={16} /> Validation failed
                </p>
                <ul className="ml-6 list-disc space-y-0.5 font-mono text-xs">
                  {validation.errors.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              </div>
            ))}
        </div>
      </div>
    </div>
  )
}
