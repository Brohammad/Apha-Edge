import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pause, Play, Rocket } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { fmtDateTime, fmtNum } from '../lib/format'
import {
  EmptyState,
  PageHeader,
  Skeleton,
  StatusBadge,
  btnGhost,
  btnPrimary,
} from '../components/ui'
import type { Paginated, StrategyDeployment } from '../lib/types'

export default function DeploymentsPage() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['strategy-deployments'],
    queryFn: () => api<Paginated<StrategyDeployment>>('/strategy-deployments'),
  })

  const pause = useMutation({
    mutationFn: (id: string) =>
      api<StrategyDeployment>(`/strategy-deployments/${id}/pause`, { method: 'POST' }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['strategy-deployments'] }),
  })

  const resume = useMutation({
    mutationFn: (id: string) =>
      api<StrategyDeployment>(`/strategy-deployments/${id}/resume`, { method: 'POST' }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['strategy-deployments'] }),
  })

  const items = data?.items ?? []

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        title="Strategy deployments"
        sub="Monitor paper deployments, last signals, and pause or resume execution."
        actions={
          <Link to="/strategies" className={btnPrimary}>
            <Rocket size={16} /> Deploy from strategy
          </Link>
        }
      />

      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<Rocket size={24} />}
          title="No active deployments"
          hint="Validate a strategy version and deploy it to paper from the strategy detail page."
        />
      ) : (
        <div className="terminal-card overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-ink-700 font-mono text-[11px] uppercase tracking-widest text-ink-300">
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Version</th>
                <th className="px-4 py-3">Qty</th>
                <th className="px-4 py-3">Last signal</th>
                <th className="px-4 py-3">Updated</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="font-mono text-xs">
              {items.map((d) => (
                <tr key={d.id} className="border-b border-ink-800 last:border-0">
                  <td className="px-4 py-2.5">
                    <StatusBadge status={d.is_active ? 'active' : 'paused'} />
                  </td>
                  <td className="px-4 py-2.5 text-ink-200">{d.strategy_version_id.slice(0, 8)}…</td>
                  <td className="px-4 py-2.5 text-ink-200">{fmtNum(d.quantity, 0)}</td>
                  <td className="px-4 py-2.5 text-ink-300">
                    {d.last_signal_action ?? '—'}
                    {d.last_signal_at ? ` @ ${fmtDateTime(d.last_signal_at)}` : ''}
                  </td>
                  <td className="px-4 py-2.5 text-ink-400">{fmtDateTime(d.updated_at)}</td>
                  <td className="px-4 py-2.5 text-right">
                    {d.is_active ? (
                      <button
                        type="button"
                        className={btnGhost}
                        disabled={pause.isPending}
                        onClick={() => pause.mutate(d.id)}
                      >
                        <Pause size={14} /> Pause
                      </button>
                    ) : (
                      <button
                        type="button"
                        className={btnGhost}
                        disabled={resume.isPending}
                        onClick={() => resume.mutate(d.id)}
                      >
                        <Play size={14} /> Resume
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
