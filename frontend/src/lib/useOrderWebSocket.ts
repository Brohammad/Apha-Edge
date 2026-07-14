import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { fetchWsTicket } from './api'
import type { Order } from './types'

const WS_BASE =
  typeof window !== 'undefined'
    ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
    : ''

export function useOrderWebSocket(enabled = true) {
  const qc = useQueryClient()
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!enabled) return

    let cancelled = false
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined

    const connect = async () => {
      try {
        const ticket = await fetchWsTicket()
        if (cancelled) return
        const ws = new WebSocket(`${WS_BASE}/api/v1/ws/orders`, ticket)
        wsRef.current = ws

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data as string) as {
              type?: string
              order_id?: string
              status?: string
              filled_quantity?: string
            }
            if (msg.type !== 'order_update' || !msg.order_id) return
            qc.setQueryData<{ items: Order[]; total_count: number } | undefined>(
              ['orders', 'list'],
              (prev) => {
                if (!prev) return prev
                return {
                  ...prev,
                  items: prev.items.map((o) =>
                    o.id === msg.order_id
                      ? {
                          ...o,
                          status: msg.status ?? o.status,
                          filled_quantity: msg.filled_quantity ?? o.filled_quantity,
                        }
                      : o,
                  ),
                }
              },
            )
          } catch {
            // ignore malformed messages
          }
        }

        ws.onclose = () => {
          if (!cancelled) {
            reconnectTimer = setTimeout(() => void connect(), 3000)
          }
        }
      } catch {
        if (!cancelled) {
          reconnectTimer = setTimeout(() => void connect(), 5000)
        }
      }
    }

    void connect()

    return () => {
      cancelled = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [enabled, qc])
}
