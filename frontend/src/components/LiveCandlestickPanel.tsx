import { useEffect, useState } from 'react'
import { CandlestickChart, type OhlcPoint } from './institutionalCharts'
import { PageHeader } from './ui'

export default function LiveCandlestickPanel({ symbol = 'AAPL' }: { symbol?: string }) {
  const [bars, setBars] = useState<OhlcPoint[]>([])
  const [status, setStatus] = useState<'connecting' | 'live' | 'idle'>('connecting')

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${protocol}://${window.location.host}/api/v1/ws/bars`)
    ws.onopen = () => setStatus('live')
    ws.onclose = () => setStatus((s) => (s === 'live' ? 'idle' : s))
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data as string) as { close?: number; timestamp?: string }
        if (msg.close && msg.timestamp) {
          setBars((prev) => {
            const last = prev[prev.length - 1]
            const next: OhlcPoint = {
              ts: msg.timestamp!,
              open: last?.close ?? msg.close!,
              high: Math.max(last?.close ?? msg.close!, msg.close!),
              low: Math.min(last?.close ?? msg.close!, msg.close!),
              close: msg.close!,
              volume: 0,
            }
            return [...prev.slice(-39), next]
          })
        }
      } catch {
        // ignore malformed frames
      }
    }
    return () => ws.close()
  }, [symbol])

  return (
    <div className="terminal-card p-4">
      <PageHeader
        title={`${symbol} OHLCV`}
        sub={
          status === 'live'
            ? 'Live WebSocket feed'
            : status === 'connecting'
              ? 'Connecting…'
              : 'Waiting for bars (no synthetic seed data)'
        }
      />
      {bars.length === 0 ? (
        <p className="text-sm text-ink-400 py-8 text-center">
          No bars yet. Live candles appear when market-data WebSocket frames arrive.
        </p>
      ) : (
        <CandlestickChart data={bars} />
      )}
    </div>
  )
}
