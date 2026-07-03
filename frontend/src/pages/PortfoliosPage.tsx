import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Wallet } from 'lucide-react'
import { api } from '../lib/api'
import { fmtMoney } from '../lib/format'
import Modal from '../components/Modal'
import {
  EmptyState,
  ErrorNote,
  PageHeader,
  Skeleton,
  btnPrimary,
  inputCls,
} from '../components/ui'
import type { Paginated, Portfolio } from '../lib/types'

export default function PortfoliosPage() {
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [capital, setCapital] = useState('100000')

  const { data, isLoading } = useQuery({
    queryKey: ['portfolios', 'all'],
    queryFn: () => api<Paginated<Portfolio>>('/portfolios', { query: { limit: 100 } }),
  })

  const create = useMutation({
    mutationFn: () =>
      api<Portfolio>('/portfolios', {
        method: 'POST',
        body: { name, initial_capital: capital, is_paper: true },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['portfolios'] })
      setShowCreate(false)
      setName('')
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
        title="Portfolios"
        sub="Paper books with live holdings, performance and risk analytics."
        actions={
          <button type="button" className={btnPrimary} onClick={() => setShowCreate(true)}>
            <Plus size={16} /> New portfolio
          </button>
        }
      />

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={<Wallet size={24} />}
          title="No portfolios yet"
          hint="Spin up a paper book and sync a backtest into it to see holdings and risk."
          action={
            <button type="button" className={btnPrimary} onClick={() => setShowCreate(true)}>
              <Plus size={16} /> Create portfolio
            </button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((p) => (
            <Link
              key={p.id}
              to={`/portfolios/${p.id}`}
              className="terminal-card animate-rise group p-5 transition hover:border-volt-500/50"
            >
              <div className="flex items-start justify-between">
                <p className="text-base font-semibold text-white group-hover:text-volt-300">
                  {p.name}
                </p>
                {p.is_paper && (
                  <span className="rounded-md border border-gold-500/30 bg-gold-500/10 px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-gold-300">
                    Paper
                  </span>
                )}
              </div>
              <p className="mt-3 font-mono text-2xl font-semibold tabular-nums text-ink-100">
                {fmtMoney(p.cash_balance, p.base_currency)}
              </p>
              <p className="mt-1 font-mono text-[11px] text-ink-400">
                cash · started at {fmtMoney(p.initial_capital, p.base_currency)}
              </p>
            </Link>
          ))}
        </div>
      )}

      {showCreate && (
        <Modal title="New portfolio" onClose={() => setShowCreate(false)}>
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
                className={inputCls}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Momentum book"
              />
            </div>
            <div>
              <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
                Initial capital (USD)
              </label>
              <input
                required
                inputMode="decimal"
                className={inputCls}
                value={capital}
                onChange={(e) => setCapital(e.target.value)}
              />
            </div>
            <button type="submit" disabled={create.isPending} className={`${btnPrimary} w-full`}>
              {create.isPending ? 'Creating…' : 'Create portfolio'}
            </button>
          </form>
        </Modal>
      )}
    </div>
  )
}
