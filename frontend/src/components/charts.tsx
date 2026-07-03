import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { fmtMoney } from '../lib/format'

export interface SeriesPoint {
  ts: string
  value: number
}

const AXIS_STYLE = {
  fontSize: 11,
  fontFamily: "'IBM Plex Mono', monospace",
  fill: '#7284a8',
}

export function EquitySparkline({
  data,
  height = 280,
  baseline,
}: {
  data: SeriesPoint[]
  height?: number
  baseline?: number
}) {
  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center font-mono text-xs text-ink-400"
        style={{ height }}
      >
        No data points
      </div>
    )
  }
  const last = data[data.length - 1].value
  const first = baseline ?? data[0].value
  const bullish = last >= first
  const stroke = bullish ? '#34d97b' : '#fb7185'
  const gradientId = bullish ? 'eq-bull' : 'eq-bear'

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
        <defs>
          <linearGradient id="eq-bull" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#34d97b" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#34d97b" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="eq-bear" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#fb7185" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#fb7185" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="#1d2436" strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="ts"
          tick={AXIS_STYLE}
          tickLine={false}
          axisLine={{ stroke: '#1d2436' }}
          minTickGap={60}
          tickFormatter={(v: string) =>
            new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
          }
        />
        <YAxis
          tick={AXIS_STYLE}
          tickLine={false}
          axisLine={false}
          width={70}
          domain={['auto', 'auto']}
          tickFormatter={(v: number) => fmtMoney(v)}
        />
        <Tooltip
          contentStyle={{
            background: '#0f131d',
            border: '1px solid #2a3349',
            borderRadius: 8,
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 12,
          }}
          labelStyle={{ color: '#a3b2cc' }}
          formatter={(value) => [fmtMoney(value as number), 'Equity']}
          labelFormatter={(v) => new Date(String(v)).toLocaleString()}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke={stroke}
          strokeWidth={2}
          fill={`url(#${gradientId})`}
          dot={false}
          isAnimationActive
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
