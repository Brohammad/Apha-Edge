import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Copy, ShoppingBag, Store, Tag } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import { fmtDateTime, fmtMoney } from '../lib/format'
import Modal from '../components/Modal'
import {
  EmptyState,
  ErrorNote,
  PageHeader,
  Skeleton,
  btnGhost,
  btnPrimary,
  inputCls,
} from '../components/ui'
import type {
  CheckoutSession,
  Organization,
  Paginated,
  Strategy,
  StrategyListing,
} from '../lib/types'

function PublishModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient()
  const [strategyId, setStrategyId] = useState('')
  const [orgId, setOrgId] = useState('')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priceCents, setPriceCents] = useState('0')

  const { data: strategies } = useQuery({
    queryKey: ['strategies', 'all'],
    queryFn: () => api<Paginated<Strategy>>('/strategies', { query: { limit: 100 } }),
  })
  const { data: orgs } = useQuery({
    queryKey: ['organizations'],
    queryFn: () => api<{ items: Organization[] }>('/organizations'),
  })

  const publish = useMutation({
    mutationFn: () =>
      api<{ id: string }>('/marketplace/listings', {
        method: 'POST',
        body: {
          strategy_id: strategyId,
          organization_id: orgId,
          title,
          description: description || null,
          price_cents: Math.round(Number(priceCents) * 100),
        },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['marketplace'] })
      onClose()
    },
  })

  return (
    <Modal title="Publish strategy" onClose={onClose}>
      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault()
          publish.mutate()
        }}
        className="space-y-4"
      >
        {publish.isError && (
          <ErrorNote
            message={publish.error instanceof Error ? publish.error.message : 'Publish failed'}
          />
        )}
        <div>
          <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
            Strategy
          </label>
          <select
            required
            className={inputCls}
            value={strategyId}
            onChange={(e) => setStrategyId(e.target.value)}
          >
            <option value="">Select…</option>
            {(strategies?.items ?? []).map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
            Organization
          </label>
          <select
            required
            className={inputCls}
            value={orgId}
            onChange={(e) => setOrgId(e.target.value)}
          >
            <option value="">Select…</option>
            {(orgs?.items ?? []).map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
          {(orgs?.items ?? []).length === 0 && (
            <p className="mt-1 text-xs text-gold-400">
              <Link to="/organizations" className="underline">
                Create an organization
              </Link>{' '}
              first.
            </p>
          )}
        </div>
        <div>
          <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
            Listing title
          </label>
          <input required className={inputCls} value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div>
          <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
            Description
          </label>
          <textarea
            className={`${inputCls} min-h-20`}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
            Price (USD)
          </label>
          <input
            required
            inputMode="decimal"
            className={inputCls}
            value={priceCents}
            onChange={(e) => setPriceCents(e.target.value)}
            placeholder="0.00 for free"
          />
        </div>
        <button type="submit" disabled={publish.isPending} className={`${btnPrimary} w-full`}>
          {publish.isPending ? 'Publishing…' : 'Publish listing'}
        </button>
      </form>
    </Modal>
  )
}

export default function MarketplacePage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const [showPublish, setShowPublish] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['marketplace', 'listings'],
    queryFn: () => api<{ items: StrategyListing[] }>('/marketplace/listings'),
  })

  const clone = useMutation({
    mutationFn: (listingId: string) =>
      api<{ strategy_id: string; name: string }>(`/marketplace/listings/${listingId}/clone`, {
        method: 'POST',
      }),
    onSuccess: (res) => {
      void qc.invalidateQueries({ queryKey: ['strategies'] })
      navigate(`/strategies/${res.strategy_id}`)
    },
  })

  const checkout = useMutation({
    mutationFn: (listingId: string) =>
      api<CheckoutSession>(`/payments/marketplace/listings/${listingId}/checkout`, {
        method: 'POST',
      }),
    onSuccess: async (session, listingId) => {
      if (session.already_purchased) {
        clone.mutate(listingId)
        return
      }
      if (session.mock && session.session_id) {
        await api('/payments/mock/complete', {
          method: 'POST',
          body: { session_id: session.session_id },
        })
        clone.mutate(listingId)
        return
      }
      if (session.checkout_url) {
        window.location.href = session.checkout_url
      }
    },
  })

  useEffect(() => {
    const mockSession = params.get('mock_checkout')
    const listingId = params.get('listing_id')
    if (mockSession && listingId) {
      void (async () => {
        await api('/payments/mock/complete', {
          method: 'POST',
          body: { session_id: mockSession },
        })
        clone.mutate(listingId)
        setParams({})
      })()
    }
  }, [params, setParams, clone])

  const items = data?.items ?? []

  const handleAcquire = (listing: StrategyListing) => {
    if (listing.price_cents === 0) {
      clone.mutate(listing.id)
    } else {
      checkout.mutate(listing.id)
    }
  }

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        title="Strategy marketplace"
        sub="Discover, purchase, and clone community strategies."
        actions={
          <button type="button" className={btnPrimary} onClick={() => setShowPublish(true)}>
            <Store size={16} /> Publish listing
          </button>
        }
      />

      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<ShoppingBag size={24} />}
          title="Marketplace is empty"
          hint="Be the first to publish a strategy from your organization."
          action={
            <button type="button" className={btnPrimary} onClick={() => setShowPublish(true)}>
              <Store size={16} /> Publish listing
            </button>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((listing) => (
            <article key={listing.id} className="terminal-card flex flex-col p-4">
              <div className="mb-2 flex items-start justify-between gap-2">
                <h3 className="font-semibold text-ink-100">{listing.title}</h3>
                <span
                  className={`shrink-0 rounded px-2 py-0.5 font-mono text-[10px] uppercase ${
                    listing.price_cents === 0
                      ? 'border border-bull-500/30 bg-bull-500/10 text-bull-300'
                      : 'border border-gold-500/30 bg-gold-500/10 text-gold-300'
                  }`}
                >
                  {listing.price_cents === 0 ? 'Free' : fmtMoney(String(listing.price_cents / 100))}
                </span>
              </div>
              {listing.description && (
                <p className="mb-3 flex-1 text-sm text-ink-300 line-clamp-3">{listing.description}</p>
              )}
              <div className="mt-auto flex items-center justify-between border-t border-ink-700 pt-3">
                <span className="flex items-center gap-1 font-mono text-[10px] text-ink-500">
                  <Tag size={11} /> {listing.clone_count} clones
                </span>
                <span className="font-mono text-[10px] text-ink-500">
                  {fmtDateTime(listing.created_at)}
                </span>
              </div>
              <button
                type="button"
                className={`${btnGhost} mt-3 w-full`}
                disabled={clone.isPending || checkout.isPending}
                onClick={() => handleAcquire(listing)}
              >
                <Copy size={14} />
                {listing.price_cents === 0 ? 'Clone strategy' : 'Purchase & clone'}
              </button>
            </article>
          ))}
        </div>
      )}

      {(clone.isError || checkout.isError) && (
        <ErrorNote
          message={
            (clone.error ?? checkout.error) instanceof Error
              ? (clone.error ?? checkout.error)!.message
              : 'Action failed'
          }
        />
      )}

      {showPublish && <PublishModal onClose={() => setShowPublish(false)} />}
    </div>
  )
}
