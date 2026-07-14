import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { fmtMoney, fmtPct } from '../lib/format'
import type { SeriesPoint } from './charts'

const AXIS_STYLE = {
  fontSize: 11,
  fontFamily: "'IBM Plex Mono', monospace",
  fill: '#7284a8',
}

export function DrawdownChart({ data, height = 220 }: { data: SeriesPoint[]; height?: number }) {
  let peak = data[0]?.value ?? 0
  const dd = data.map((p) => {
    peak = Math.max(peak, p.value)
    return { ts: p.ts, drawdown: peak > 0 ? (p.value - peak) / peak : 0 }
  })
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={dd} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
        <CartesianGrid stroke="#1d2436" strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="ts" tick={AXIS_STYLE} tickLine={false} axisLine={{ stroke: '#1d2436' }} />
        <YAxis tick={AXIS_STYLE} tickFormatter={(v) => fmtPct(v)} width={60} />
        <Tooltip formatter={(v) => [fmtPct(v as number), 'Drawdown']} />
        <Bar dataKey="drawdown" fill="#fb7185" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function ReturnsHistogram({
  returns,
  height = 220,
}: {
  returns: number[]
  height?: number
}) {
  const buckets = returns.reduce<Record<string, number>>((acc, r) => {
    const key = (Math.round(r * 100) / 100).toFixed(2)
    acc[key] = (acc[key] ?? 0) + 1
    return acc
  }, {})
  const data = Object.entries(buckets).map(([bin, count]) => ({ bin, count }))
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data}>
        <CartesianGrid stroke="#1d2436" vertical={false} />
        <XAxis dataKey="bin" tick={AXIS_STYLE} />
        <YAxis tick={AXIS_STYLE} />
        <Bar dataKey="count" fill="#6ee7ff" />
      </BarChart>
    </ResponsiveContainer>
  )
}

export interface OhlcPoint {
  ts: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export function CandlestickChart({ data, height = 320 }: { data: OhlcPoint[]; height?: number }) {
  const chartData = data.map((d) => ({
    ...d,
    body: [Math.min(d.open, d.close), Math.max(d.open, d.close)],
    wick: [d.low, d.high],
  }))
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={chartData}>
        <CartesianGrid stroke="#1d2436" vertical={false} />
        <XAxis dataKey="ts" tick={AXIS_STYLE} />
        <YAxis tick={AXIS_STYLE} tickFormatter={(v) => fmtMoney(v)} width={70} />
        <Tooltip />
        <Bar dataKey="body" fill="#34d97b" barSize={6} />
        <Line type="monotone" dataKey="close" stroke="#6ee7ff" dot={false} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
