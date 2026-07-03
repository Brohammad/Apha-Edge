import { Fragment } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, BrainCircuit } from 'lucide-react'
import { api } from '../lib/api'
import { fmtDateTime } from '../lib/format'
import { ErrorNote, PageHeader, Skeleton, StatusBadge } from '../components/ui'
import type { InsightDetail } from '../lib/types'

const TYPE_LABELS: Record<string, string> = {
  strategy_explanation: 'Strategy explanation',
  performance_report: 'Performance report',
  risk_interpretation: 'Risk interpretation',
  trade_summary: 'Trade summary',
}

function metaString(metadata: Record<string, unknown>, key: string): string | null {
  const value = metadata[key]
  return typeof value === 'string' || typeof value === 'number' ? String(value) : null
}

function InsightMetadata({ metadata, createdAt }: { metadata: Record<string, unknown>; createdAt: string }) {
  const provider = metaString(metadata, 'llm_provider')
  const configured = metaString(metadata, 'llm_provider_configured')
  const model = metaString(metadata, 'model')
  const promptVersion = metaString(metadata, 'prompt_version')
  const insightType = metaString(metadata, 'insight_type')
  const promptTokens = metaString(metadata, 'prompt_tokens')
  const completionTokens = metaString(metadata, 'completion_tokens')
  const totalTokens = metaString(metadata, 'total_tokens')
  const isMock = provider === 'mock'
  const configuredOpenAiButMock =
    configured === 'openai' && provider === 'mock'

  const rows: { label: string; value: string }[] = [
    provider && { label: 'Provider used', value: provider },
    configured && configured !== provider && {
      label: 'Provider configured',
      value: configured,
    },
    model && { label: 'Model', value: model },
    promptVersion && { label: 'Prompt version', value: promptVersion },
    insightType && { label: 'Insight type', value: insightType.replace(/_/g, ' ') },
    promptTokens && { label: 'Prompt tokens', value: promptTokens },
    completionTokens && { label: 'Completion tokens', value: completionTokens },
    totalTokens && { label: 'Total tokens', value: totalTokens },
    { label: 'Generated', value: fmtDateTime(createdAt) },
  ].filter((row): row is { label: string; value: string } => Boolean(row))

  return (
    <div className="mt-6 space-y-4 border-t border-ink-700 pt-4">
      {isMock && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          <strong className="font-semibold">Demo mode.</strong>{' '}
          {configuredOpenAiButMock ? (
            <>
              <code className="text-amber-100">LLM_PROVIDER=openai</code> is set but{' '}
              <code className="text-amber-100">OPENAI_API_KEY</code> is missing, so AlphaEdge
              fell back to the local mock generator.
            </>
          ) : (
            <>
              This report was synthesized locally without calling an external LLM. Set{' '}
              <code className="text-amber-100">LLM_PROVIDER=openai</code> and{' '}
              <code className="text-amber-100">OPENAI_API_KEY</code> in the API environment for
              live AI analysis.
            </>
          )}
        </div>
      )}
      <dl className="grid gap-3 sm:grid-cols-2">
        {rows.map(({ label, value }) => (
          <div key={label} className="rounded-lg border border-ink-700/80 bg-ink-900/40 px-3 py-2">
            <dt className="font-mono text-[10px] uppercase tracking-wide text-ink-400">{label}</dt>
            <dd className="mt-0.5 font-mono text-xs text-ink-100">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

// Minimal markdown-ish renderer: headings, bullets, bold, paragraphs.
function renderContent(content: string) {
  const lines = content.split('\n')
  return lines.map((line, i) => {
    const trimmed = line.trim()
    if (trimmed === '') return <div key={i} className="h-3" />
    if (trimmed.startsWith('### '))
      return (
        <h4 key={i} className="mt-4 mb-1 text-sm font-bold text-white">
          {trimmed.slice(4)}
        </h4>
      )
    if (trimmed.startsWith('## '))
      return (
        <h3 key={i} className="mt-5 mb-1.5 text-base font-bold text-white">
          {trimmed.slice(3)}
        </h3>
      )
    if (trimmed.startsWith('# '))
      return (
        <h2 key={i} className="mt-5 mb-2 text-lg font-bold text-white">
          {trimmed.slice(2)}
        </h2>
      )
    const bullet = trimmed.startsWith('- ') || trimmed.startsWith('* ')
    const text = bullet ? trimmed.slice(2) : trimmed
    const parts = text.split(/\*\*(.+?)\*\*/g)
    const rendered = parts.map((p, j) =>
      j % 2 === 1 ? (
        <strong key={j} className="font-semibold text-ink-100">
          {p}
        </strong>
      ) : (
        <Fragment key={j}>{p}</Fragment>
      ),
    )
    if (bullet)
      return (
        <p key={i} className="ml-4 text-sm leading-relaxed text-ink-200">
          • {rendered}
        </p>
      )
    return (
      <p key={i} className="text-sm leading-relaxed text-ink-200">
        {rendered}
      </p>
    )
  })
}

export default function InsightDetailPage() {
  const { insightId } = useParams<{ insightId: string }>()

  const { data } = useQuery({
    queryKey: ['insight', insightId],
    queryFn: () => api<InsightDetail>(`/insights/${insightId}`),
    refetchInterval: (q) => {
      const s = q.state.data?.request.status
      return s === 'queued' || s === 'running' ? 4_000 : false
    },
  })

  if (!data) {
    return (
      <div className="mx-auto max-w-4xl space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  const { request, report } = data
  const pending = request.status === 'queued' || request.status === 'running'

  return (
    <div className="mx-auto max-w-4xl">
      <Link
        to="/insights"
        className="mb-3 inline-flex items-center gap-1 text-sm text-ink-300 hover:text-volt-300"
      >
        <ArrowLeft size={14} /> Insights
      </Link>
      <PageHeader
        title={TYPE_LABELS[request.insight_type] ?? request.insight_type}
        sub={`Requested ${fmtDateTime(request.created_at)}`}
        actions={<StatusBadge status={request.status} />}
      />

      {request.status === 'failed' && (
        <ErrorNote message={request.error_message ?? 'Insight generation failed'} />
      )}

      {pending && (
        <div className="terminal-card flex items-center gap-3 px-5 py-4">
          <BrainCircuit size={18} className="animate-pulse text-volt-400" />
          <p className="text-sm text-ink-200">
            The model is thinking — this page refreshes automatically.
          </p>
        </div>
      )}

      {report && (
        <div className="terminal-card animate-rise p-6">
          <div className="prose-invert">{renderContent(report.content)}</div>
          <InsightMetadata metadata={report.metadata} createdAt={report.created_at} />
        </div>
      )}
    </div>
  )
}
