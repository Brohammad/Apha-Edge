import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { fmtInr } from '../lib/format'
import { PageHeader, Skeleton } from '../components/ui'
import type { Instrument, Paginated } from '../lib/types'

const INDIAN_EXCHANGES = ['ALL', 'NSE', 'BSE'] as const

export default function IndianMarketsPage() {
  const [exchange, setExchange] = useState<(typeof INDIAN_EXCHANGES)[number]>('ALL')

  const { data, isLoading } = useQuery({
    queryKey: ['instruments', 'indian'],
    queryFn: () => api<Paginated<Instrument>>('/instruments', { query: { limit: 100 } }),
  })

  const instruments = useMemo(() => {
    const items = (data?.items ?? []).filter(
      (i) => i.currency === 'INR' || i.exchange === 'NSE' || i.exchange === 'BSE',
    )
    if (exchange === 'ALL') return items
    return items.filter((i) => i.exchange === exchange)
  }, [data, exchange])

  return (
    <div className="space-y-6">
      <PageHeader
        title="Indian Markets"
        subtitle="NSE/BSE instruments with INR formatting"
      />

      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm text-ink-300">Exchange</span>
        {INDIAN_EXCHANGES.map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => setExchange(ex)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
              exchange === ex
                ? 'bg-volt-500/20 text-volt-300 ring-1 ring-volt-500/40'
                : 'bg-surface-800 text-ink-300 hover:text-ink-100'
            }`}
          >
            {ex}
          </button>
        ))}
      </div>

      <div className="terminal-card overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-surface-700 bg-surface-900/80 font-mono text-xs uppercase text-ink-400">
            <tr>
              <th className="px-4 py-3">Symbol</th>
              <th className="px-4 py-3">Exchange</th>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3 text-right">Ref. price (INR)</th>
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i} className="border-b border-surface-800">
                  <td colSpan={4} className="px-4 py-3">
                    <Skeleton className="h-4 w-full" />
                  </td>
                </tr>
              ))}
            {!isLoading && instruments.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-ink-400">
                  No instruments for this exchange. Run seed_data to load NSE/BSE symbols.
                </td>
              </tr>
            )}
            {instruments.map((inst) => (
              <tr key={inst.id} className="border-b border-surface-800 hover:bg-surface-800/50">
                <td className="px-4 py-3 font-mono font-medium text-ink-100">{inst.symbol}</td>
                <td className="px-4 py-3 text-ink-300">{inst.exchange}</td>
                <td className="px-4 py-3 text-ink-200">{inst.name}</td>
                <td className="px-4 py-3 text-right font-mono text-volt-300">
                  {fmtInr(refPrice(inst.symbol))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function refPrice(symbol: string): number {
  const map: Record<string, number> = {
    RELIANCE: 2850,
    TCS: 4100,
    INFY: 1850,
    HDFCBANK: 1650,
    SBIN: 820,
  }
  return map[symbol] ?? 1000
}
