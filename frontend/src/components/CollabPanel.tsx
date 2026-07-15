import { useCallback, useEffect, useRef, useState } from 'react'
import { Users, Wifi, WifiOff } from 'lucide-react'
import { api, fetchWsTicket } from '../lib/api'
import { btnPrimary } from './ui'
import type { CollabSessionInfo } from '../lib/types'

interface CollabPanelProps {
  strategyId: string
  code: string
  onRemoteEdit: (source: string) => void
  joinSessionId?: string | null
}

export default function CollabPanel({
  strategyId,
  code,
  onRemoteEdit,
  joinSessionId,
}: CollabPanelProps) {
  const [session, setSession] = useState<CollabSessionInfo | null>(null)
  const [connected, setConnected] = useState(false)
  const [peerCount, setPeerCount] = useState(0)
  const [cursors, setCursors] = useState<Record<string, { line: number; column: number }>>({})
  const wsRef = useRef<WebSocket | null>(null)
  const lastSentRef = useRef('')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const cursorDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const startSession = async () => {
    const res = await api<CollabSessionInfo>('/collaboration/sessions', {
      method: 'POST',
      body: { strategy_id: strategyId },
    })
    setSession(res)
  }

  const connect = useCallback(
    async (sessionId: string) => {
      const ticket = await fetchWsTicket()
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.host
      const url = `${proto}//${host}/api/v1/collaboration/ws/${sessionId}`

      const ws = new WebSocket(url, [`ticket.${ticket}`])
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
            user_id?: string
            payload?: {
              source_code?: string
              peer_count?: number
              line?: number
              column?: number
            }
          }
          if (
            (msg.type === 'join' || msg.type === 'leave') &&
            typeof msg.payload?.peer_count === 'number'
          ) {
            setPeerCount(msg.payload.peer_count)
          }
          if (msg.type === 'cursor' && typeof msg.payload?.line === 'number') {
            setCursors((prev) => {
              const next = { ...prev }
              if (msg.user_id) {
                next[msg.user_id] = {
                  line: msg.payload!.line!,
                  column: msg.payload?.column ?? 0,
                }
              }
              return next
            })
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
    if (joinSessionId && !session) {
      setSession({ session_id: joinSessionId, strategy_id: strategyId })
    }
  }, [joinSessionId, session, strategyId])

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

  useEffect(() => {
    if (!connected || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    if (cursorDebounceRef.current) clearTimeout(cursorDebounceRef.current)
    cursorDebounceRef.current = setTimeout(() => {
      const lines = code.split('\n')
      wsRef.current?.send(
        JSON.stringify({
          type: 'cursor',
          payload: { line: lines.length, column: (lines.at(-1) ?? '').length },
        }),
      )
    }, 250)
    return () => {
      if (cursorDebounceRef.current) clearTimeout(cursorDebounceRef.current)
    }
  }, [code, connected])

  const shareUrl = session
    ? `${window.location.origin}${window.location.pathname}?collab=${session.session_id}`
    : ''

  const cursorEntries = Object.entries(cursors)

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
          {cursorEntries.length > 0 ? (
            <ul className="space-y-1 font-mono text-[10px] text-ink-400">
              {cursorEntries.map(([uid, pos]) => (
                <li key={uid}>
                  peer {uid.slice(0, 8)}… @ L{pos.line}:C{pos.column}
                </li>
              ))}
            </ul>
          ) : null}
          <p className="text-xs text-ink-500">
            Share the URL — peers join with their own login; edits and cursors sync in real time.
          </p>
        </div>
      )}
    </div>
  )
}
