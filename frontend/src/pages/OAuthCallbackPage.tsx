import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { ErrorNote } from '../components/ui'

function readHashParams(): URLSearchParams {
  const hash = window.location.hash.startsWith('#')
    ? window.location.hash.slice(1)
    : window.location.hash
  return new URLSearchParams(hash)
}

export default function OAuthCallbackPage() {
  const navigate = useNavigate()
  const { completeOAuthLogin } = useAuth()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const run = async () => {
      const queryError = new URLSearchParams(window.location.search).get('error')
      if (queryError) {
        setError(queryError.replace(/_/g, ' '))
        return
      }

      const access = readHashParams().get('access_token')
      if (!access) {
        setError('Sign-in was cancelled or did not return a token.')
        return
      }

      try {
        window.history.replaceState(null, '', window.location.pathname)
        await completeOAuthLogin(access)
        navigate('/', { replace: true })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'OAuth sign-in failed')
      }
    }

    void run()
  }, [completeOAuthLogin, navigate])

  if (error) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 px-6">
        <ErrorNote message={error} />
        <button
          type="button"
          className="font-mono text-sm text-volt-400 hover:text-volt-300"
          onClick={() => navigate('/login', { replace: true })}
        >
          Back to sign in
        </button>
      </div>
    )
  }

  return (
    <div className="flex h-screen items-center justify-center">
      <p className="font-mono text-sm text-ink-300">Completing sign-in…</p>
    </div>
  )
}
