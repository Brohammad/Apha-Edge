import { useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { MessageCircle, Send } from 'lucide-react'
import { api } from '../lib/api'
import { PageHeader, btnPrimary, inputCls, ErrorNote } from '../components/ui'

interface AskResponse {
  answer: string
  sources: Array<{ title: string; url: string }>
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export default function AssistantPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')

  const ask = useMutation({
    mutationFn: (question: string) =>
      api<AskResponse>('/insights/ask', { method: 'POST', body: { question } }),
    onSuccess: (data, question) => {
      setMessages((prev) => [
        ...prev,
        { role: 'user', content: question },
        { role: 'assistant', content: data.answer },
      ])
      setInput('')
    },
  })

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    const q = input.trim()
    if (!q || ask.isPending) return
    ask.mutate(q)
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-3xl flex-col">
      <PageHeader
        title="Research Assistant"
        sub="Ask questions about markets, strategies, and fundamentals."
      />

      <div className="terminal-card mb-4 flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-ink-400">
            <MessageCircle size={32} />
            <p className="text-sm">Start a conversation about any ticker or strategy concept.</p>
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`max-w-[85%] rounded-lg px-4 py-3 text-sm ${
              m.role === 'user'
                ? 'ml-auto bg-volt-500/15 text-volt-100'
                : 'bg-surface-800 text-ink-100'
            }`}
          >
            {m.content}
          </div>
        ))}
      </div>

      {ask.isError && (
        <ErrorNote
          message={ask.error instanceof Error ? ask.error.message : 'Request failed'}
        />
      )}

      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          className={`${inputCls} flex-1`}
          placeholder="Ask about AAPL earnings, RSI strategies, risk limits…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button type="submit" disabled={ask.isPending} className={btnPrimary}>
          <Send size={16} />
          {ask.isPending ? '…' : 'Send'}
        </button>
      </form>
    </div>
  )
}
