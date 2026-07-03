import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  BrainCircuit,
  CandlestickChart,
  FlaskConical,
  LayoutDashboard,
  LogOut,
  ScrollText,
  ShoppingBag,
  SlidersHorizontal,
  Users,
  Wallet,
} from 'lucide-react'
import MarketClock from './MarketClock'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import type { Instrument, Paginated, Quote } from '../lib/types'

const TAPE_SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'SPY']

const NAV = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/strategies', label: 'Strategies', icon: FlaskConical },
  { to: '/backtests', label: 'Backtests', icon: CandlestickChart },
  { to: '/optimizations', label: 'Optimizer', icon: SlidersHorizontal },
  { to: '/portfolios', label: 'Portfolios', icon: Wallet },
  { to: '/orders', label: 'Orders', icon: ScrollText },
  { to: '/marketplace', label: 'Marketplace', icon: ShoppingBag },
  { to: '/organizations', label: 'Organizations', icon: Users },
  { to: '/insights', label: 'AI Insights', icon: BrainCircuit },
]

interface TapeEntry {
  symbol: string
  close: number
  changePct: number | null
  live: boolean
}

function useTickerTape(): TapeEntry[] {
  const { data: instruments } = useQuery({
    queryKey: ['instruments', 'tape'],
    queryFn: () => api<Paginated<Instrument>>('/instruments', { query: { limit: 10 } }),
    staleTime: 5 * 60_000,
  })

  const symbols =
    instruments?.items.length ? instruments.items.map((i) => i.symbol) : TAPE_SYMBOLS

  const { data: tape } = useQuery({
    queryKey: ['tape-quotes', symbols.join(',')],
    enabled: symbols.length > 0,
    refetchInterval: 60_000,
    staleTime: 30_000,
    queryFn: async () => {
      const quotes = await api<{ items: Quote[] }>('/market-data/quotes', {
        query: { symbols: symbols.join(',') },
      })
      return quotes.items.map((q) => ({
        symbol: q.symbol,
        close: Number(q.price),
        changePct: q.change_pct !== null ? Number(q.change_pct) : null,
        live: q.source === 'alpha_vantage',
      }))
    },
  })

  return tape ?? []
}

function TickerTape() {
  const entries = useTickerTape()
  if (entries.length === 0) return null
  const doubled = [...entries, ...entries]
  return (
    <div className="relative overflow-hidden border-b border-ink-700 bg-ink-900/80">
      <div className="flex w-max animate-ticker gap-8 px-4 py-1.5">
        {doubled.map((e, i) => (
          <span key={i} className="flex items-center gap-2 font-mono text-xs whitespace-nowrap">
            <span className="font-semibold text-ink-100">
              {e.symbol}
              {e.live && <span className="ml-1 text-bull-500">●</span>}
            </span>
            <span className="tabular-nums text-ink-200">{e.close.toFixed(2)}</span>
            {e.changePct !== null && (
              <span
                className={`tabular-nums ${e.changePct >= 0 ? 'text-bull-400' : 'text-bear-400'}`}
              >
                {e.changePct >= 0 ? '▲' : '▼'} {Math.abs(e.changePct).toFixed(2)}%
              </span>
            )}
          </span>
        ))}
      </div>
    </div>
  )
}

function MarketStatus() {
  const { data } = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const res = await fetch('/api/v1/health/ready')
      return res.ok
    },
    refetchInterval: 30_000,
    retry: false,
  })
  const ok = data !== false
  return (
    <div className="flex items-center gap-2 px-3 py-2">
      <span
        className={`h-2 w-2 rounded-full ${ok ? 'animate-pulse-dot bg-bull-500' : 'bg-bear-500'}`}
      />
      <span className="font-mono text-[11px] uppercase tracking-widest text-ink-300">
        {ok ? 'Systems Live' : 'API Offline'}
      </span>
    </div>
  )
}

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="flex w-56 shrink-0 flex-col border-r border-ink-700 bg-ink-900/70 backdrop-blur">
        <div className="flex items-center gap-2.5 border-b border-ink-700 px-4 py-4">
          <div className="glow-volt flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-volt-500 to-bull-500">
            <Activity size={20} className="text-ink-950" strokeWidth={2.5} />
          </div>
          <div>
            <p className="text-sm font-bold tracking-tight text-white">AlphaEdge</p>
            <p className="font-mono text-[10px] uppercase tracking-widest text-ink-300">
              Trading Terminal
            </p>
          </div>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? 'bg-volt-500/10 text-volt-300 shadow-[inset_2px_0_0_0_theme(colors.volt.400)]'
                    : 'text-ink-200 hover:bg-ink-800 hover:text-ink-100'
                }`
              }
            >
              <Icon size={17} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-ink-700">
          <MarketStatus />
          <MarketClock />
          <div className="flex items-center justify-between gap-2 border-t border-ink-700 px-3 py-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-ink-100">{user?.display_name}</p>
              <p className="truncate font-mono text-[11px] text-ink-300">{user?.email}</p>
            </div>
            <button
              type="button"
              title="Sign out"
              className="rounded-lg p-2 text-ink-300 transition hover:bg-ink-800 hover:text-bear-400"
              onClick={() => {
                void logout().then(() => navigate('/login'))
              }}
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <TickerTape />
        <main className="relative flex-1 overflow-y-auto p-6">
          <div className="pointer-events-none absolute inset-0 overflow-hidden opacity-[0.03]">
            <div className="h-px w-full animate-scan bg-gradient-to-r from-transparent via-volt-400 to-transparent" />
          </div>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
