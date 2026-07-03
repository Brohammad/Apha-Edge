import { useMemo, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Ban, Link2, Plus, ScrollText, Send } from 'lucide-react'
import { api } from '../lib/api'
import { fmtDateTime, fmtMoney, fmtNum } from '../lib/format'
import Modal from '../components/Modal'
import {
  EmptyState,
  ErrorNote,
  PageHeader,
  Skeleton,
  StatusBadge,
  btnBear,
  btnPrimary,
  inputCls,
} from '../components/ui'
import type {
  BrokerConnection,
  Instrument,
  LiveTradingStatus,
  Order,
  Paginated,
  Portfolio,
} from '../lib/types'

function NewOrderModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient()
  const [portfolioId, setPortfolioId] = useState('')
  const [connectionId, setConnectionId] = useState('')
  const [instrumentId, setInstrumentId] = useState('')
  const [side, setSide] = useState<'buy' | 'sell'>('buy')
  const [orderType, setOrderType] = useState<'market' | 'limit' | 'stop'>('market')
  const [quantity, setQuantity] = useState('10')
  const [limitPrice, setLimitPrice] = useState('')
  const [stopPrice, setStopPrice] = useState('')
  const [liveAck, setLiveAck] = useState(false)

  const { data: portfolios } = useQuery({
    queryKey: ['portfolios', 'all'],
    queryFn: () => api<Paginated<Portfolio>>('/portfolios', { query: { limit: 100 } }),
  })
  const { data: connections } = useQuery({
    queryKey: ['broker-connections'],
    queryFn: () => api<Paginated<BrokerConnection>>('/broker-connections'),
  })
  const { data: instruments } = useQuery({
    queryKey: ['instruments', 'all'],
    queryFn: () => api<Paginated<Instrument>>('/instruments', { query: { limit: 200 } }),
  })

  const selectedConnection = (connections?.items ?? []).find((c) => c.id === connectionId)
  const isLiveOrder = selectedConnection && !selectedConnection.is_paper

  const submit = useMutation({
    mutationFn: () =>
      api<Order>('/orders', {
        method: 'POST',
        body: {
          portfolio_id: portfolioId,
          broker_connection_id: connectionId,
          instrument_id: instrumentId,
          side,
          order_type: orderType,
          quantity,
          limit_price: orderType === 'limit' ? limitPrice || null : null,
          stop_price: orderType === 'stop' ? stopPrice || null : null,
          live_trading_acknowledged: isLiveOrder ? liveAck : false,
        },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['orders'] })
      onClose()
    },
  })

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    submit.mutate()
  }

  return (
    <Modal title="Place order" onClose={onClose}>
      <form onSubmit={onSubmit} className="space-y-4">
        {submit.isError && (
          <ErrorNote
            message={submit.error instanceof Error ? submit.error.message : 'Order failed'}
          />
        )}
        <div className="grid grid-cols-2 gap-2">
          {(['buy', 'sell'] as const).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setSide(s)}
              className={`rounded-lg border px-3 py-2.5 font-mono text-sm font-bold uppercase tracking-wider transition ${
                side === s
                  ? s === 'buy'
                    ? 'border-bull-500 bg-bull-500/15 text-bull-300'
                    : 'border-bear-500 bg-bear-500/15 text-bear-300'
                  : 'border-ink-600 text-ink-300 hover:border-ink-400'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <div>
          <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
            Portfolio
          </label>
          <select
            required
            className={inputCls}
            value={portfolioId}
            onChange={(e) => setPortfolioId(e.target.value)}
          >
            <option value="">Select…</option>
            {(portfolios?.items ?? []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
            Broker connection
          </label>
          <select
            required
            className={inputCls}
            value={connectionId}
            onChange={(e) => setConnectionId(e.target.value)}
          >
            <option value="">Select…</option>
            {(connections?.items ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.broker_name} {c.is_paper ? '(paper)' : '(live)'}
              </option>
            ))}
          </select>
        </div>
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
            <option value="">Select…</option>
            {(instruments?.items ?? []).map((i) => (
              <option key={i.id} value={i.id}>
                {i.symbol} — {i.name}
              </option>
            ))}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Type
            </label>
            <select
              className={inputCls}
              value={orderType}
              onChange={(e) => setOrderType(e.target.value as typeof orderType)}
            >
              <option value="market">Market</option>
              <option value="limit">Limit</option>
              <option value="stop">Stop</option>
            </select>
          </div>
          <div>
            <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Quantity
            </label>
            <input
              required
              inputMode="decimal"
              className={inputCls}
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
            />
          </div>
        </div>
        {orderType === 'limit' && (
          <div>
            <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Limit price
            </label>
            <input
              required
              inputMode="decimal"
              className={inputCls}
              value={limitPrice}
              onChange={(e) => setLimitPrice(e.target.value)}
            />
          </div>
        )}
        {orderType === 'stop' && (
          <div>
            <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Stop price
            </label>
            <input
              required
              inputMode="decimal"
              className={inputCls}
              value={stopPrice}
              onChange={(e) => setStopPrice(e.target.value)}
            />
          </div>
        )}
        {isLiveOrder && (
          <label className="flex items-start gap-2 rounded-lg border border-bear-500/40 bg-bear-500/10 p-3 text-sm text-bear-200">
            <input
              type="checkbox"
              checked={liveAck}
              onChange={(e) => setLiveAck(e.target.checked)}
              className="mt-0.5"
            />
            <span>
              I understand this order routes to a <strong>live</strong> broker account with real
              capital at risk.
            </span>
          </label>
        )}
        <button
          type="submit"
          disabled={submit.isPending || (isLiveOrder && !liveAck)}
          className={`${side === 'buy' ? btnPrimary : btnBear} w-full`}
        >
          <Send size={15} />
          {submit.isPending ? 'Submitting…' : `Submit ${side} order`}
        </button>
      </form>
    </Modal>
  )
}

function BrokerConnections() {
  const qc = useQueryClient()
  const [showAlpaca, setShowAlpaca] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [isPaper, setIsPaper] = useState(true)

  const { data: liveStatus } = useQuery({
    queryKey: ['live-trading-status'],
    queryFn: () => api<LiveTradingStatus>('/broker-connections/live-trading/status', { auth: false }),
  })

  const { data } = useQuery({
    queryKey: ['broker-connections'],
    queryFn: () => api<Paginated<BrokerConnection>>('/broker-connections'),
  })

  const create = useMutation({
    mutationFn: () =>
      api<BrokerConnection>('/broker-connections', {
        method: 'POST',
        body: {
          broker_name: 'alpaca',
          is_paper: isPaper,
          credentials: { api_key: apiKey, api_secret: apiSecret },
        },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['broker-connections'] })
      setShowAlpaca(false)
      setApiKey('')
      setApiSecret('')
    },
  })

  const createPaper = useMutation({
    mutationFn: () =>
      api<BrokerConnection>('/broker-connections', {
        method: 'POST',
        body: { broker_name: 'paper', is_paper: true },
      }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['broker-connections'] }),
  })

  const items = data?.items ?? []

  return (
    <div className="terminal-card p-4">
      <div className="mb-3 flex items-center justify-between">
        <p className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-ink-300">
          <Link2 size={13} /> Broker connections
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            className="text-xs font-medium text-volt-400 hover:text-volt-300 disabled:opacity-50"
            disabled={createPaper.isPending}
            onClick={() => createPaper.mutate()}
          >
            + Paper
          </button>
          <button
            type="button"
            className="text-xs font-medium text-gold-400 hover:text-gold-300"
            onClick={() => setShowAlpaca(true)}
          >
            + Alpaca
          </button>
        </div>
      </div>

      {liveStatus && (
        <div
          className={`mb-3 rounded-lg border px-3 py-2 text-xs ${
            liveStatus.live_trading_enabled
              ? 'border-bull-500/30 bg-bull-500/10 text-bull-300'
              : 'border-gold-500/30 bg-gold-500/10 text-gold-300'
          }`}
        >
          Live trading: {liveStatus.live_trading_enabled ? 'ENABLED' : 'disabled (paper only)'}
        </div>
      )}

      {items.length === 0 ? (
        <p className="text-sm text-ink-400">
          No connections — add paper or Alpaca to start routing orders.
        </p>
      ) : (
        <ul className="space-y-2">
          {items.map((c) => (
            <li
              key={c.id}
              className="flex items-center justify-between rounded-lg border border-ink-700 bg-ink-900/50 px-3 py-2"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`h-2 w-2 rounded-full ${c.is_active ? 'bg-bull-500' : 'bg-ink-500'}`}
                />
                <span className="font-mono text-sm font-semibold uppercase text-ink-100">
                  {c.broker_name}
                </span>
                {c.is_paper ? (
                  <span className="rounded border border-gold-500/30 bg-gold-500/10 px-1.5 py-0.5 font-mono text-[10px] uppercase text-gold-300">
                    paper
                  </span>
                ) : (
                  <span className="rounded border border-bear-500/30 bg-bear-500/10 px-1.5 py-0.5 font-mono text-[10px] uppercase text-bear-300">
                    live
                  </span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {showAlpaca && (
        <Modal title="Connect Alpaca" onClose={() => setShowAlpaca(false)}>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              create.mutate()
            }}
            className="mt-3 space-y-3"
          >
            {create.isError && (
              <ErrorNote
                message={create.error instanceof Error ? create.error.message : 'Connect failed'}
              />
            )}
            <div className="flex gap-2">
              {([true, false] as const).map((paper) => (
                <button
                  key={String(paper)}
                  type="button"
                  onClick={() => setIsPaper(paper)}
                  className={`flex-1 rounded-lg border px-3 py-2 font-mono text-xs uppercase ${
                    isPaper === paper
                      ? paper
                        ? 'border-gold-500 bg-gold-500/15 text-gold-300'
                        : 'border-bear-500 bg-bear-500/15 text-bear-300'
                      : 'border-ink-600 text-ink-400'
                  }`}
                >
                  {paper ? 'Paper' : 'Live'}
                </button>
              ))}
            </div>
            {!isPaper && !liveStatus?.live_trading_enabled && (
              <p className="text-xs text-bear-400">
                Live trading is disabled on this server. Use paper mode or enable LIVE_TRADING_ENABLED.
              </p>
            )}
            <input
              required
              placeholder="API key"
              className={inputCls}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
            <input
              required
              type="password"
              placeholder="API secret"
              className={inputCls}
              value={apiSecret}
              onChange={(e) => setApiSecret(e.target.value)}
            />
            <button
              type="submit"
              disabled={create.isPending || (!isPaper && !liveStatus?.live_trading_enabled)}
              className={`${btnPrimary} w-full`}
            >
              {create.isPending ? 'Connecting…' : 'Connect Alpaca'}
            </button>
          </form>
        </Modal>
      )}
    </div>
  )
}

export default function OrdersPage() {
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['orders', 'list'],
    queryFn: () => api<Paginated<Order>>('/orders', { query: { limit: 100 } }),
    refetchInterval: 8_000,
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

  const cancel = useMutation({
    mutationFn: (orderId: string) => api<Order>(`/orders/${orderId}`, { method: 'DELETE' }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['orders'] }),
  })

  const items = data?.items ?? []
  const cancellable = new Set(['pending', 'submitted', 'partially_filled'])

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        title="Order blotter"
        sub="Route paper orders through the execution engine and track fills."
        actions={
          <button type="button" className={btnPrimary} onClick={() => setShowCreate(true)}>
            <Plus size={16} /> Place order
          </button>
        }
      />

      <div className="mb-6">
        <BrokerConnections />
      </div>

      {isLoading ? (
        <Skeleton className="h-80 w-full" />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<ScrollText size={24} />}
          title="Blotter is empty"
          hint="Place your first paper order — no real money will move."
          action={
            <button type="button" className={btnPrimary} onClick={() => setShowCreate(true)}>
              <Plus size={16} /> Place order
            </button>
          }
        />
      ) : (
        <div className="terminal-card overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-ink-700 font-mono text-[11px] uppercase tracking-widest text-ink-300">
                <th className="px-4 py-3 font-medium">Symbol</th>
                <th className="px-4 py-3 font-medium">Side</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 text-right font-medium">Qty</th>
                <th className="px-4 py-3 text-right font-medium">Filled</th>
                <th className="px-4 py-3 text-right font-medium">Limit</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Placed</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody className="font-mono text-xs">
              {items.map((o) => (
                <tr key={o.id} className="border-b border-ink-800 last:border-0">
                  <td className="px-4 py-2.5 font-semibold text-ink-100">
                    {symbolById.get(o.instrument_id) ?? o.instrument_id.slice(0, 8)}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`font-bold uppercase ${
                        o.side === 'buy' ? 'text-bull-400' : 'text-bear-400'
                      }`}
                    >
                      {o.side}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 uppercase text-ink-300">{o.order_type}</td>
                  <td className="px-4 py-2.5 text-right text-ink-200">{fmtNum(o.quantity, 0)}</td>
                  <td className="px-4 py-2.5 text-right text-ink-200">
                    {fmtNum(o.filled_quantity, 0)}
                  </td>
                  <td className="px-4 py-2.5 text-right text-ink-300">
                    {o.limit_price ? fmtMoney(o.limit_price) : '—'}
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={o.status} />
                  </td>
                  <td className="px-4 py-2.5 text-ink-300">{fmtDateTime(o.created_at)}</td>
                  <td className="px-4 py-2.5 text-right">
                    {cancellable.has(o.status) && (
                      <button
                        type="button"
                        title="Cancel order"
                        className="rounded p-1 text-ink-400 transition hover:bg-bear-500/10 hover:text-bear-400"
                        onClick={() => cancel.mutate(o.id)}
                      >
                        <Ban size={14} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && <NewOrderModal onClose={() => setShowCreate(false)} />}
    </div>
  )
}
