import { useEffect, useState } from 'react'
import { CandlestickChart, type OhlcPoint } from './institutionalCharts'
import { PageHeader } from './ui'

function seedBars(): OhlcPoint[] {
  let price = 150
  return Array.from({ length: 40 }, (_, i) => {
    const open = price
    const close = open + (Math.random() - 0.48) * 3
    const high = Math.max(open, close) + Math.random() * 2
    const low = Math.min(open, close) - Math.random() * 2
    price = close
    return {
      ts: new Date(Date.now() - (39 - i) * 60000).toISOString(),
      open,
      high,
      low,
      close,
      volume: Math.floor(Math.random() * 1e6),
    }
  })
}

export default function LiveCandlestickPanel({ symbol = 'AAPL' }: { symbol?: string }) {
  const [bars, setBars] = useState<OhlcPoint[]>(seedBars)

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${protocol}://${window.location.host}/api/v1/ws/bars`)
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
      <PageHeader title={`${symbol} OHLCV`} sub="Live WebSocket feed" />
      <CandlestickChart data={bars} />
    </div>
  )
}
