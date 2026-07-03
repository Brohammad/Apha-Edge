import { useEffect, useState } from 'react'

function isMarketOpen(now: Date): boolean {
  const utc = now.getUTCDay()
  if (utc === 0 || utc === 6) return false
  const mins = now.getUTCHours() * 60 + now.getUTCMinutes()
  // NYSE regular session ~14:30–21:00 UTC (approx; no holiday calendar)
  return mins >= 14 * 60 + 30 && mins < 21 * 60
}

export default function MarketClock() {
  const [now, setNow] = useState(() => new Date())

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  const open = isMarketOpen(now)
  const time = now.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })

  return (
    <div className="flex items-center gap-3 border-t border-ink-700 px-3 py-2.5">
      <span
        className={`h-2 w-2 rounded-full ${open ? 'animate-pulse-dot bg-bull-500' : 'bg-ink-500'}`}
      />
      <div className="min-w-0 flex-1">
        <p className="font-mono text-[10px] uppercase tracking-widest text-ink-400">
          {open ? 'NYSE Open' : 'After Hours'}
        </p>
        <p className="font-mono text-sm tabular-nums text-ink-100">{time} UTC</p>
      </div>
    </div>
  )
}
