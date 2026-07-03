import { useMemo, type ReactNode } from 'react'
import { Activity } from 'lucide-react'

interface Candle {
  x: number
  open: number
  close: number
  high: number
  low: number
}

function makeCandles(count: number): Candle[] {
  // Deterministic pseudo-random walk so the hero chart is stable across renders.
  let seed = 42
  const rand = () => {
    seed = (seed * 16807) % 2147483647
    return seed / 2147483647
  }
  const candles: Candle[] = []
  let price = 50
  for (let i = 0; i < count; i++) {
    const drift = (rand() - 0.44) * 8
    const open = price
    const close = Math.max(12, Math.min(88, open + drift))
    const high = Math.max(open, close) + rand() * 4
    const low = Math.min(open, close) - rand() * 4
    candles.push({ x: i, open, close, high, low })
    price = close
  }
  return candles
}

function CandleHero() {
  const candles = useMemo(() => makeCandles(36), [])
  const w = 100 / candles.length
  return (
    <svg
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      className="absolute inset-0 h-full w-full opacity-40"
      aria-hidden
    >
      {candles.map((c, i) => {
        const bull = c.close >= c.open
        const color = bull ? 'var(--color-bull-500)' : 'var(--color-bear-500)'
        const cx = i * w + w / 2
        const top = 100 - Math.max(c.open, c.close)
        const height = Math.max(0.8, Math.abs(c.close - c.open))
        return (
          <g key={i}>
            <line
              x1={cx}
              x2={cx}
              y1={100 - c.high}
              y2={100 - c.low}
              stroke={color}
              strokeWidth="0.3"
            />
            <rect x={i * w + w * 0.22} y={top} width={w * 0.56} height={height} fill={color}>
              <animate
                attributeName="opacity"
                values="0.6;1;0.6"
                dur={`${2.4 + (i % 5) * 0.4}s`}
                repeatCount="indefinite"
              />
            </rect>
          </g>
        )
      })}
    </svg>
  )
}

export default function AuthShell({ children, title, sub }: {
  children: ReactNode
  title: string
  sub: string
}) {
  return (
    <div className="flex min-h-screen">
      <div className="relative hidden flex-1 flex-col justify-between overflow-hidden border-r border-ink-700 bg-ink-900 p-10 lg:flex">
        <CandleHero />
        <div className="pointer-events-none absolute inset-x-0 h-px animate-scan bg-gradient-to-r from-transparent via-volt-500/60 to-transparent" />
        <div className="relative flex items-center gap-3">
          <div className="glow-volt flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-volt-500 to-bull-500">
            <Activity size={24} className="text-ink-950" strokeWidth={2.5} />
          </div>
          <div>
            <p className="text-lg font-bold tracking-tight text-white">AlphaEdge</p>
            <p className="font-mono text-[11px] uppercase tracking-widest text-ink-300">
              Quant Trading Terminal
            </p>
          </div>
        </div>
        <div className="relative max-w-md">
          <h2 className="text-3xl font-bold leading-tight text-white">
            Build. Backtest.
            <br />
            <span className="bg-gradient-to-r from-volt-400 to-bull-400 bg-clip-text text-transparent">
              Beat the market.
            </span>
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-ink-200">
            Strategy DSL, event-driven backtesting with C++ acceleration, walk-forward
            optimization, portfolio risk analytics and AI-generated insights — all in one terminal.
          </p>
          <div className="mt-6 flex gap-6 font-mono text-xs text-ink-300">
            <div>
              <p className="text-xl font-semibold text-bull-400">10M+</p>
              <p>events / sec</p>
            </div>
            <div>
              <p className="text-xl font-semibold text-volt-400">62x</p>
              <p>C++ speedup</p>
            </div>
            <div>
              <p className="text-xl font-semibold text-gold-400">VaR</p>
              <p>risk engine</p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex w-full flex-col items-center justify-center px-6 lg:max-w-[480px]">
        <div className="w-full max-w-sm animate-rise">
          <h1 className="text-2xl font-bold tracking-tight text-white">{title}</h1>
          <p className="mt-1 text-sm text-ink-300">{sub}</p>
          <div className="mt-8">{children}</div>
        </div>
      </div>
    </div>
  )
}
