import { useCallback, useEffect, useRef, useState } from 'react'
import { Users, Wifi, WifiOff } from 'lucide-react'
import { api, loadTokens } from '../lib/api'
import { btnPrimary } from './ui'
import type { CollabSessionInfo } from '../lib/types'

interface CollabPanelProps {
  strategyId: string
  code: string
  onRemoteEdit: (source: string) => void
}

export default function CollabPanel({ strategyId, code, onRemoteEdit }: CollabPanelProps) {
  const [session, setSession] = useState<CollabSessionInfo | null>(null)
  const [connected, setConnected] = useState(false)
  const [peerCount, setPeerCount] = useState(0)
  const wsRef = useRef<WebSocket | null>(null)
  const lastSentRef = useRef('')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const startSession = async () => {
    const res = await api<CollabSessionInfo>('/collaboration/sessions', {
      method: 'POST',
      body: { strategy_id: strategyId },
    })
    setSession(res)
  }

  const connect = useCallback(
    (sessionId: string) => {
      const tokens = loadTokens()
      if (!tokens) return

      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.host
      const url = `${proto}//${host}/api/v1/collaboration/ws/${sessionId}?token=${encodeURIComponent(tokens.access_token)}`

      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        setPeerCount(1)
      }
      ws.onclose = () => {
        setConnected(false)
        setPeerCount(0)
      }
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data as string) as {
            type: string
            payload?: { source_code?: string }
          }
          if (msg.type === 'join' || msg.type === 'leave') {
            setPeerCount((c) => (msg.type === 'join' ? c + 1 : Math.max(0, c - 1)))
          }
          if (msg.type === 'edit' && typeof msg.payload?.source_code === 'string') {
            onRemoteEdit(msg.payload.source_code)
          }
        } catch {
          // ignore malformed messages
        }
      }
    },
    [onRemoteEdit],
  )

  useEffect(() => {
    if (session?.session_id) {
      connect(session.session_id)
    }
    return () => {
      wsRef.current?.close()
    }
  }, [session?.session_id, connect])

  useEffect(() => {
    if (!connected || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    if (code === lastSentRef.current) return

    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      lastSentRef.current = code
      wsRef.current?.send(
        JSON.stringify({ type: 'edit', payload: { source_code: code } }),
      )
    }, 400)

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [code, connected])

  const shareUrl = session
    ? `${window.location.origin}${window.location.pathname}?collab=${session.session_id}`
    : ''

  return (
    <div className="terminal-card p-4">
      <div className="mb-3 flex items-center justify-between">
        <p className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-ink-300">
          <Users size={13} /> Live collaboration
        </p>
        {connected ? (
          <span className="flex items-center gap-1 font-mono text-[10px] text-bull-400">
            <Wifi size={12} /> {peerCount} connected
          </span>
        ) : session ? (
          <span className="flex items-center gap-1 font-mono text-[10px] text-ink-500">
            <WifiOff size={12} /> connecting…
          </span>
        ) : null}
      </div>

      {!session ? (
        <button type="button" className={btnPrimary} onClick={() => void startSession()}>
          Start collab session
        </button>
      ) : (
        <div className="space-y-2">
          <p className="font-mono text-xs text-ink-400">
            Session{' '}
            <code className="text-volt-300">{session.session_id.slice(0, 8)}…</code>
          </p>
          <input
            readOnly
            className="w-full rounded-lg border border-ink-700 bg-ink-950/60 px-3 py-2 font-mono text-[11px] text-ink-300"
            value={shareUrl}
            onFocus={(e) => e.target.select()}
          />
          <p className="text-xs text-ink-500">
            Share the URL — peers join with their own login and edits sync in real time.
          </p>
        </div>
      )}
    </div>
  )
}
