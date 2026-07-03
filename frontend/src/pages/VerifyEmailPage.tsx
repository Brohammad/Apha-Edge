import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import type { User } from '../lib/types'

export default function VerifyEmailPage() {
  const [params] = useSearchParams()
  const [status, setStatus] = useState<'pending' | 'ok' | 'error'>('pending')
  const [message, setMessage] = useState('Verifying your email…')

  useEffect(() => {
    const token = params.get('token')
    if (!token) {
      setStatus('error')
      setMessage('Missing verification token.')
      return
    }
    api<User>('/auth/verify-email', { method: 'POST', body: { token }, auth: false })
      .then(() => {
        setStatus('ok')
        setMessage('Email verified. You can now use trading features.')
      })
      .catch(() => {
        setStatus('error')
        setMessage('Verification link is invalid or expired.')
      })
  }, [params])

  return (
    <div className="flex h-screen flex-col items-center justify-center gap-4 px-6">
      <p
        className={`font-mono text-sm ${status === 'error' ? 'text-red-400' : status === 'ok' ? 'text-emerald-400' : 'text-ink-300'}`}
      >
        {message}
      </p>
      {status === 'ok' && (
        <Link to="/" className="text-sm text-accent hover:underline">
          Go to dashboard
        </Link>
      )}
    </div>
  )
}
