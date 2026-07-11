import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  GitBranch,
  Play,
  Rocket,
  Save,
  ShieldCheck,
  Trash2,
  XCircle,
} from 'lucide-react'
import { api } from '../lib/api'
import { fmtDateTime } from '../lib/format'
import CollabPanel from '../components/CollabPanel'
import Modal from '../components/Modal'
import {
  ErrorNote,
  PageHeader,
  Skeleton,
  StatusBadge,
  btnBear,
  btnGhost,
  btnPrimary,
  inputCls,
} from '../components/ui'
import type {
  BrokerConnection,
  Indicator,
  Instrument,
  Paginated,
  Portfolio,
  Strategy,
  StrategyDeployment,
  StrategyVersion,
  ValidationResult,
} from '../lib/types'

function parseParameters(raw: Record<string, unknown>): Array<[string, string]> {
  return Object.entries(raw).map(([k, v]) => [k, String(v)])
}

function parametersToObject(rows: Array<[string, string]>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [k, v] of rows) {
    const key = k.trim()
    if (!key) continue
    const num = Number(v)
    out[key] = v !== '' && !Number.isNaN(num) && v.trim() === String(num) ? num : v
  }
  return out
}

const INDICATOR_SNIPPETS: Record<string, string> = {
  sma: 'sma(period)',
  ema: 'ema(period)',
  rsi: 'rsi(14)',
  macd: 'macd(12)',
  bollinger: 'bollinger(20)',
}

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

  const { data: indicators } = useQuery({
    queryKey: ['indicators'],
    queryFn: () => api<Paginated<Indicator>>('/indicators'),
  })

  const sorted = useMemo(
    () => [...(versions?.items ?? [])].sort((a, b) => b.version - a.version),
    [versions],
  )
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const selected = sorted.find((v) => v.id === selectedId) ?? sorted[0] ?? null

  const [code, setCode] = useState('')
  const [paramRows, setParamRows] = useState<Array<[string, string]>>([])
  const [dirty, setDirty] = useState(false)
  const [validation, setValidation] = useState<ValidationResult | null>(null)
  const [showDeploy, setShowDeploy] = useState(false)
  const [deployPortfolioId, setDeployPortfolioId] = useState('')
  const [deployBrokerId, setDeployBrokerId] = useState('')
  const [deployInstrumentId, setDeployInstrumentId] = useState('')
  const [deployQty, setDeployQty] = useState('10')

  useEffect(() => {
    setCode(selected?.source_code ?? '')
    setParamRows(parseParameters(selected?.parameters ?? {}))
    setDirty(false)
    setValidation(null)
  }, [selected?.id, selected?.source_code, selected?.parameters])

  const { data: portfolios } = useQuery({
    queryKey: ['portfolios', 'all'],
    queryFn: () => api<Paginated<Portfolio>>('/portfolios', { query: { limit: 100 } }),
    enabled: showDeploy,
  })

  const { data: brokers } = useQuery({
    queryKey: ['broker-connections'],
    queryFn: () => api<Paginated<BrokerConnection>>('/broker-connections'),
    enabled: showDeploy,
  })

  const { data: instruments } = useQuery({
    queryKey: ['instruments', 'all'],
    queryFn: () => api<Paginated<Instrument>>('/instruments', { query: { limit: 200 } }),
    enabled: showDeploy,
  })

  const saveVersion = useMutation({
    mutationFn: () =>
      api<StrategyVersion>(`/strategies/${strategyId}/versions`, {
        method: 'POST',
        body: { source_code: code, parameters: parametersToObject(paramRows) },
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

  const deploy = useMutation({
    mutationFn: () =>
      api<StrategyDeployment>('/strategy-deployments', {
        method: 'POST',
        body: {
          strategy_version_id: selected!.id,
          portfolio_id: deployPortfolioId,
          broker_connection_id: deployBrokerId,
          instrument_ids: [deployInstrumentId],
          quantity: deployQty,
        },
      }),
    onSuccess: () => {
      setShowDeploy(false)
      void qc.invalidateQueries({ queryKey: ['strategy-deployments'] })
    },
  })

  const remove = useMutation({
    mutationFn: () => api(`/strategies/${strategyId}`, { method: 'DELETE' }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['strategies'] })
      navigate('/strategies')
    },
  })

  const canBacktest = Boolean(selected?.status === 'validated' && !dirty)
  const paperBrokers = (brokers?.items ?? []).filter((b) => b.is_paper && b.is_active)

  const validateAndBacktest = async () => {
    if (!selected) return
    let versionId = selected.id
    if (dirty) {
      const saved = await saveVersion.mutateAsync()
      versionId = saved.id
    }
    const res = await validate.mutateAsync(versionId)
    if (res.errors.length === 0) {
      navigate(`/backtests?strategy_version_id=${versionId}`)
    }
  }

  const insertSnippet = (snippet: string) => {
    setCode((prev) => (prev.endsWith('\n') || prev.length === 0 ? prev : `${prev}\n`) + snippet)
    setDirty(true)
  }

  const submitDeploy = (e: FormEvent) => {
    e.preventDefault()
    deploy.mutate()
  }

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
            <button
              type="button"
              className={btnGhost}
              disabled={!canBacktest}
              title={
                dirty
                  ? 'Save changes first'
                  : selected?.status !== 'validated'
                    ? 'Validate before backtesting'
                    : undefined
              }
              onClick={() => void validateAndBacktest()}
            >
              <Play size={15} /> Validate &amp; Backtest
            </button>
            <button
              type="button"
              className={btnPrimary}
              disabled={selected?.status !== 'validated' || dirty}
              onClick={() => setShowDeploy(true)}
            >
              <Rocket size={15} /> Deploy to paper
            </button>
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

      <div className="grid gap-5 lg:grid-cols-[260px_1fr_200px]">
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
                      <p className="font-mono text-sm font-semibold text-ink-100">v{v.version}</p>
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
          <CollabPanel
            strategyId={strategyId!}
            code={code}
            onRemoteEdit={(source) => {
              setCode(source)
              setDirty(true)
            }}
          />

          <div className="terminal-card p-4">
            <p className="mb-2 font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Parameters
            </p>
            <div className="space-y-2">
              {paramRows.map(([key, value], idx) => (
                <div key={idx} className="flex gap-2">
                  <input
                    className={inputCls}
                    placeholder="key"
                    value={key}
                    onChange={(e) => {
                      const next = [...paramRows]
                      next[idx] = [e.target.value, value]
                      setParamRows(next)
                      setDirty(true)
                    }}
                  />
                  <input
                    className={inputCls}
                    placeholder="value"
                    value={value}
                    onChange={(e) => {
                      const next = [...paramRows]
                      next[idx] = [key, e.target.value]
                      setParamRows(next)
                      setDirty(true)
                    }}
                  />
                </div>
              ))}
              <button
                type="button"
                className={btnGhost}
                onClick={() => {
                  setParamRows([...paramRows, ['', '']])
                  setDirty(true)
                }}
              >
                + Add parameter
              </button>
            </div>
          </div>

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

        <div className="terminal-card h-fit p-4">
          <p className="mb-3 font-mono text-[11px] uppercase tracking-widest text-ink-300">
            Indicators
          </p>
          <ul className="space-y-1">
            {(indicators?.items ?? []).map((ind) => (
              <li key={ind.id}>
                <button
                  type="button"
                  className="w-full rounded px-2 py-1.5 text-left font-mono text-xs text-ink-200 hover:bg-ink-800"
                  onClick={() =>
                    insertSnippet(INDICATOR_SNIPPETS[ind.name] ?? `${ind.name}(period)`)
                  }
                >
                  {ind.name}
                </button>
              </li>
            ))}
          </ul>
          {strategy.strategy_type === 'dsl' && (
            <p className="mt-3 text-[10px] leading-relaxed text-ink-400">
              DSL supports crossover, crossunder, comparisons (&lt;, &gt;), and all()/any().
            </p>
          )}
        </div>
      </div>

      {showDeploy && (
      <Modal onClose={() => setShowDeploy(false)} title="Deploy to paper">
        <form onSubmit={submitDeploy} className="space-y-4">
          <p className="text-sm text-ink-300">
            Active deployments evaluate signals on each ingested bar and submit paper orders.
          </p>
          <label className="block text-sm">
            Portfolio
            <select
              className={`${inputCls} mt-1 w-full`}
              value={deployPortfolioId}
              onChange={(e) => setDeployPortfolioId(e.target.value)}
              required
            >
              <option value="">Select portfolio…</option>
              {(portfolios?.items ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            Paper broker
            <select
              className={`${inputCls} mt-1 w-full`}
              value={deployBrokerId}
              onChange={(e) => setDeployBrokerId(e.target.value)}
              required
            >
              <option value="">Select broker…</option>
              {paperBrokers.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.broker_name} (paper)
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            Instrument
            <select
              className={`${inputCls} mt-1 w-full`}
              value={deployInstrumentId}
              onChange={(e) => setDeployInstrumentId(e.target.value)}
              required
            >
              <option value="">Select instrument…</option>
              {(instruments?.items ?? []).map((i) => (
                <option key={i.id} value={i.id}>
                  {i.symbol}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            Order quantity
            <input
              className={`${inputCls} mt-1 w-full`}
              value={deployQty}
              onChange={(e) => setDeployQty(e.target.value)}
              required
            />
          </label>
          {deploy.isError && (
            <ErrorNote
              message={deploy.error instanceof Error ? deploy.error.message : 'Deploy failed'}
            />
          )}
          <div className="flex justify-end gap-2">
            <button type="button" className={btnGhost} onClick={() => setShowDeploy(false)}>
              Cancel
            </button>
            <button type="submit" className={btnPrimary} disabled={deploy.isPending}>
              {deploy.isPending ? 'Deploying…' : 'Deploy'}
            </button>
          </div>
        </form>
      </Modal>
      )}
    </div>
  )
}
