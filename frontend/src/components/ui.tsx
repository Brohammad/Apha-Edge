import type { ReactNode } from 'react'
import { Loader2, TrendingDown, TrendingUp } from 'lucide-react'

const STATUS_STYLES: Record<string, string> = {
  queued: 'bg-gold-500/15 text-gold-300 border-gold-500/30',
  pending: 'bg-gold-500/15 text-gold-300 border-gold-500/30',
  running: 'bg-volt-500/15 text-volt-300 border-volt-500/30',
  submitted: 'bg-volt-500/15 text-volt-300 border-volt-500/30',
  completed: 'bg-bull-500/15 text-bull-300 border-bull-500/30',
  filled: 'bg-bull-500/15 text-bull-300 border-bull-500/30',
  validated: 'bg-bull-500/15 text-bull-300 border-bull-500/30',
  published: 'bg-volt-500/15 text-volt-300 border-volt-500/30',
  partially_filled: 'bg-volt-500/15 text-volt-300 border-volt-500/30',
  failed: 'bg-bear-500/15 text-bear-300 border-bear-500/30',
  rejected: 'bg-bear-500/15 text-bear-300 border-bear-500/30',
  cancelled: 'bg-ink-600/30 text-ink-300 border-ink-600',
  draft: 'bg-ink-600/30 text-ink-300 border-ink-600',
}

export function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? 'bg-ink-600/30 text-ink-300 border-ink-600'
  const active = status === 'running'
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wider ${style}`}
    >
      {active && <Loader2 size={11} className="animate-spin" />}
      {status.replace(/_/g, ' ')}
    </span>
  )
}

export function StatCard({
  label,
  value,
  sub,
  accent,
  icon,
}: {
  label: string
  value: ReactNode
  sub?: ReactNode
  accent?: 'bull' | 'bear' | 'volt' | 'neutral'
  icon?: ReactNode
}) {
  const valueColor =
    accent === 'bull'
      ? 'text-bull-400'
      : accent === 'bear'
        ? 'text-bear-400'
        : accent === 'volt'
          ? 'text-volt-400'
          : 'text-ink-100'
  return (
    <div className="terminal-card animate-rise p-4">
      <div className="flex items-center justify-between">
        <p className="font-mono text-[11px] font-medium uppercase tracking-widest text-ink-300">
          {label}
        </p>
        {icon && <span className="text-ink-400">{icon}</span>}
      </div>
      <p className={`mt-2 font-mono text-2xl font-semibold tabular-nums ${valueColor}`}>{value}</p>
      {sub !== undefined && <div className="mt-1 text-xs text-ink-300">{sub}</div>}
    </div>
  )
}

export function DeltaTag({ value }: { value: number }) {
  const up = value >= 0
  return (
    <span
      className={`inline-flex items-center gap-1 font-mono text-xs font-medium ${up ? 'text-bull-400' : 'text-bear-400'}`}
    >
      {up ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
      {(value * 100).toFixed(2)}%
    </span>
  )
}

export function PageHeader({
  title,
  sub,
  actions,
}: {
  title: string
  sub?: string
  actions?: ReactNode
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">{title}</h1>
        {sub && <p className="mt-1 text-sm text-ink-300">{sub}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}

export function EmptyState({
  icon,
  title,
  hint,
  action,
}: {
  icon: ReactNode
  title: string
  hint?: string
  action?: ReactNode
}) {
  return (
    <div className="terminal-card flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full border border-ink-600 bg-ink-800 text-ink-300">
        {icon}
      </div>
      <p className="text-base font-semibold text-ink-100">{title}</p>
      {hint && <p className="max-w-sm text-sm text-ink-300">{hint}</p>}
      {action}
    </div>
  )
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} />
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-bear-500/40 bg-bear-500/10 px-4 py-3 font-mono text-sm text-bear-300">
      {message}
    </div>
  )
}

export const inputCls =
  'w-full rounded-lg border border-ink-600 bg-ink-900 px-3 py-2 text-sm text-ink-100 placeholder:text-ink-400 outline-none transition focus:border-volt-500 focus:ring-2 focus:ring-volt-500/20'

export const btnPrimary =
  'inline-flex items-center justify-center gap-2 rounded-lg bg-volt-500 px-4 py-2 text-sm font-semibold text-ink-950 transition hover:bg-volt-400 disabled:cursor-not-allowed disabled:opacity-50'

export const btnGhost =
  'inline-flex items-center justify-center gap-2 rounded-lg border border-ink-600 bg-ink-800/60 px-4 py-2 text-sm font-medium text-ink-100 transition hover:border-ink-400 hover:bg-ink-700 disabled:cursor-not-allowed disabled:opacity-50'

export const btnBull =
  'inline-flex items-center justify-center gap-2 rounded-lg bg-bull-500 px-4 py-2 text-sm font-semibold text-ink-950 transition hover:bg-bull-400 disabled:cursor-not-allowed disabled:opacity-50'

export const btnBear =
  'inline-flex items-center justify-center gap-2 rounded-lg bg-bear-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-bear-400 disabled:cursor-not-allowed disabled:opacity-50'
