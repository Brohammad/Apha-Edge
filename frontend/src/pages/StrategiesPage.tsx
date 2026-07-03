import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FlaskConical, Plus } from 'lucide-react'
import { api } from '../lib/api'
import { fmtDate } from '../lib/format'
import Modal from '../components/Modal'
import {
  EmptyState,
  ErrorNote,
  PageHeader,
  Skeleton,
  btnPrimary,
  inputCls,
} from '../components/ui'
import type { Paginated, Strategy } from '../lib/types'

const DSL_TEMPLATE = `name: golden-cross
parameters:
  fast: 10
  slow: 30
signals:
  - when: crossover(sma(fast), sma(slow))
    then: BUY
  - when: crossunder(sma(fast), sma(slow))
    then: SELL
`

export default function StrategiesPage() {
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [type, setType] = useState<'dsl' | 'python'>('dsl')
  const [description, setDescription] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['strategies', 'list'],
    queryFn: () =>
      api<Paginated<Strategy>>('/strategies', { query: { limit: 100, active_only: false } }),
  })

  const create = useMutation({
    mutationFn: () =>
      api<Strategy>('/strategies', {
        method: 'POST',
        body: {
          name,
          strategy_type: type,
          description: description || null,
          source_code: type === 'dsl' ? DSL_TEMPLATE : null,
        },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['strategies'] })
      setShowCreate(false)
      setName('')
      setDescription('')
    },
  })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    create.mutate()
  }

  const items = data?.items ?? []

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        title="Strategies"
        sub="Design and version your alpha — YAML DSL or raw Python."
        actions={
          <button type="button" className={btnPrimary} onClick={() => setShowCreate(true)}>
            <Plus size={16} /> New strategy
          </button>
        }
      />

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-36 w-full" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={<FlaskConical size={24} />}
          title="No strategies yet"
          hint="Every edge starts with an idea. Create your first strategy — we'll pre-fill a golden-cross DSL template."
          action={
            <button type="button" className={btnPrimary} onClick={() => setShowCreate(true)}>
              <Plus size={16} /> Create strategy
            </button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((s) => (
            <Link
              key={s.id}
              to={`/strategies/${s.id}`}
              className="terminal-card animate-rise group p-5 transition hover:border-volt-500/50"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-base font-semibold text-white group-hover:text-volt-300">
                  {s.name}
                </p>
                <span
                  className={`rounded-md border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider ${
                    s.strategy_type === 'dsl'
                      ? 'border-volt-500/30 bg-volt-500/10 text-volt-300'
                      : 'border-gold-500/30 bg-gold-500/10 text-gold-300'
                  }`}
                >
                  {s.strategy_type}
                </span>
              </div>
              <p className="mt-2 line-clamp-2 min-h-10 text-sm text-ink-300">
                {s.description || 'No description'}
              </p>
              <div className="mt-3 flex items-center justify-between font-mono text-[11px] text-ink-400">
                <span>Updated {fmtDate(s.updated_at)}</span>
                <span
                  className={`flex items-center gap-1.5 ${s.is_active ? 'text-bull-400' : 'text-ink-400'}`}
                >
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${s.is_active ? 'bg-bull-500' : 'bg-ink-500'}`}
                  />
                  {s.is_active ? 'active' : 'inactive'}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {showCreate && (
        <Modal title="New strategy" onClose={() => setShowCreate(false)}>
          <form onSubmit={submit} className="space-y-4">
            {create.isError && (
              <ErrorNote
                message={create.error instanceof Error ? create.error.message : 'Creation failed'}
              />
            )}
            <div>
              <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
                Name
              </label>
              <input
                required
                maxLength={255}
                className={inputCls}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Golden Cross v1"
              />
            </div>
            <div>
              <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
                Type
              </label>
              <div className="grid grid-cols-2 gap-2">
                {(['dsl', 'python'] as const).map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setType(t)}
                    className={`rounded-lg border px-3 py-2 font-mono text-sm uppercase transition ${
                      type === t
                        ? 'border-volt-500 bg-volt-500/10 text-volt-300'
                        : 'border-ink-600 text-ink-300 hover:border-ink-400'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
                Description
              </label>
              <textarea
                className={`${inputCls} min-h-20 resize-y`}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What edge does this capture?"
              />
            </div>
            <button type="submit" disabled={create.isPending} className={`${btnPrimary} w-full`}>
              {create.isPending ? 'Creating…' : 'Create strategy'}
            </button>
          </form>
        </Modal>
      )}
    </div>
  )
}
