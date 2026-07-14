import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { ErrorNote } from '../components/ui'

export default function OAuthCallbackPage() {
  const navigate = useNavigate()
  const { completeOAuthLogin } = useAuth()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const run = async () => {
      const params = new URLSearchParams(window.location.search)
      const queryError = params.get('error')
      if (queryError) {
        setError(queryError.replace(/_/g, ' '))
        return
      }

      if (params.get('oauth') !== 'success') {
        setError('Sign-in was cancelled or did not complete.')
        return
      }

      try {
        window.history.replaceState(null, '', window.location.pathname)
        await completeOAuthLogin()
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
