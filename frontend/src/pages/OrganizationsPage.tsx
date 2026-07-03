import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building2, Plus } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { api } from '../lib/api'
import { fmtDateTime } from '../lib/format'
import Modal from '../components/Modal'
import {
  EmptyState,
  ErrorNote,
  PageHeader,
  Skeleton,
  btnPrimary,
  inputCls,
} from '../components/ui'
import type { Organization } from '../lib/types'

function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 40)
}

export default function OrganizationsPage() {
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['organizations'],
    queryFn: () => api<{ items: Organization[] }>('/organizations'),
  })

  const create = useMutation({
    mutationFn: () =>
      api<Organization>('/organizations', {
        method: 'POST',
        body: { name, slug: slug || slugify(name) },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['organizations'] })
      setShowCreate(false)
      setName('')
      setSlug('')
    },
  })

  const items = data?.items ?? []

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader
        title="Organizations"
        sub="Multi-tenant desks for publishing strategies to the marketplace."
        actions={
          <button type="button" className={btnPrimary} onClick={() => setShowCreate(true)}>
            <Plus size={16} /> New organization
          </button>
        }
      />

      {isLoading ? (
        <Skeleton className="h-48 w-full" />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<Building2 size={24} />}
          title="No organizations yet"
          hint="Create a desk to publish strategies on the marketplace."
          action={
            <button type="button" className={btnPrimary} onClick={() => setShowCreate(true)}>
              <Plus size={16} /> Create organization
            </button>
          }
        />
      ) : (
        <div className="terminal-card divide-y divide-ink-700">
          {items.map((org) => (
            <div key={org.id} className="flex items-center justify-between px-4 py-4">
              <div>
                <p className="font-semibold text-ink-100">{org.name}</p>
                <p className="font-mono text-xs text-ink-400">/{org.slug}</p>
              </div>
              <div className="text-right">
                <span className="rounded border border-ink-600 px-2 py-0.5 font-mono text-[10px] uppercase text-ink-300">
                  {org.plan_tier}
                </span>
                <p className="mt-1 font-mono text-[10px] text-ink-500">
                  {fmtDateTime(org.created_at)}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreate && (
        <Modal title="New organization" onClose={() => setShowCreate(false)}>
          <form
            onSubmit={(e: FormEvent) => {
              e.preventDefault()
              create.mutate()
            }}
            className="space-y-4"
          >
            {create.isError && (
              <ErrorNote
                message={create.error instanceof Error ? create.error.message : 'Create failed'}
              />
            )}
            <div>
              <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
                Name
              </label>
              <input
                required
                className={inputCls}
                value={name}
                onChange={(e) => {
                  setName(e.target.value)
                  if (!slug) setSlug(slugify(e.target.value))
                }}
              />
            </div>
            <div>
              <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
                Slug
              </label>
              <input
                required
                className={inputCls}
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="alpha-quant-desk"
              />
            </div>
            <button type="submit" disabled={create.isPending} className={`${btnPrimary} w-full`}>
              {create.isPending ? 'Creating…' : 'Create organization'}
            </button>
          </form>
        </Modal>
      )}
    </div>
  )
}
