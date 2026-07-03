import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { fmtDateTime } from '../lib/format'
import { StatusBadge } from './ui'
import type { BacktestRun, InsightRequest, Order, Paginated } from '../lib/types'

interface FeedItem {
  id: string
  ts: string
  label: string
  href: string
  status: string
  kind: 'backtest' | 'order' | 'insight'
}

export default function ActivityFeed() {
  const backtests = useQuery({
    queryKey: ['backtests', 'feed'],
    queryFn: () => api<Paginated<BacktestRun>>('/backtest-runs', { query: { limit: 5 } }),
    refetchInterval: 12_000,
  })
  const orders = useQuery({
    queryKey: ['orders', 'feed'],
    queryFn: () => api<Paginated<Order>>('/orders', { query: { limit: 5 } }),
    refetchInterval: 12_000,
  })
  const insights = useQuery({
    queryKey: ['insights', 'feed'],
    queryFn: () => api<Paginated<InsightRequest>>('/insights', { query: { limit: 5 } }),
    refetchInterval: 15_000,
  })

  const items = useMemo(() => {
    const feed: FeedItem[] = []
    for (const r of backtests.data?.items ?? []) {
      feed.push({
        id: r.id,
        ts: r.created_at,
        label: r.name,
        href: `/backtests/${r.id}`,
        status: r.status,
        kind: 'backtest',
      })
    }
    for (const o of orders.data?.items ?? []) {
      feed.push({
        id: o.id,
        ts: o.created_at,
        label: `${o.side.toUpperCase()} ×${o.quantity}`,
        href: '/orders',
        status: o.status,
        kind: 'order',
      })
    }
    for (const i of insights.data?.items ?? []) {
      feed.push({
        id: i.id,
        ts: i.created_at,
        label: i.insight_type.replace(/_/g, ' '),
        href: `/insights/${i.id}`,
        status: i.status,
        kind: 'insight',
      })
    }
    return feed.sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime()).slice(0, 8)
  }, [backtests.data, orders.data, insights.data])

  const kindLabel = { backtest: 'BT', order: 'ORD', insight: 'AI' } as const

  return (
    <div className="terminal-card animate-rise p-5">
      <div className="mb-4 flex items-center justify-between">
        <p className="font-mono text-[11px] uppercase tracking-widest text-ink-300">
          Live activity
        </p>
        <span className="flex items-center gap-1.5 font-mono text-[10px] text-ink-400">
          <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-volt-400" />
          streaming
        </span>
      </div>
      {items.length === 0 ? (
        <p className="py-6 text-center text-sm text-ink-400">
          The floor is quiet — submit a backtest to get things moving.
        </p>
      ) : (
        <ul className="space-y-1">
          {items.map((item) => (
            <li key={`${item.kind}-${item.id}`}>
              <Link
                to={item.href}
                className="group flex items-center gap-3 rounded-lg px-2 py-2 transition hover:bg-ink-800/60"
              >
                <span
                  className={`shrink-0 rounded border px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wider ${
                    item.kind === 'backtest'
                      ? 'border-volt-500/30 bg-volt-500/10 text-volt-300'
                      : item.kind === 'order'
                        ? 'border-gold-500/30 bg-gold-500/10 text-gold-300'
                        : 'border-bull-500/30 bg-bull-500/10 text-bull-300'
                  }`}
                >
                  {kindLabel[item.kind]}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-ink-100 group-hover:text-volt-300">
                    {item.label}
                  </p>
                  <p className="font-mono text-[10px] text-ink-400">{fmtDateTime(item.ts)}</p>
                </div>
                <StatusBadge status={item.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
