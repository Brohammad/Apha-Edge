import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { saveTokens } from '../lib/api'

export default function OAuthCallbackPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()

  useEffect(() => {
    const access = params.get('access_token')
    const refresh = params.get('refresh_token')
    if (access && refresh) {
      saveTokens({ access_token: access, refresh_token: refresh, token_type: 'bearer' })
      navigate('/', { replace: true })
    } else {
      navigate('/login', { replace: true })
    }
  }, [params, navigate])

  return (
    <div className="flex h-screen items-center justify-center">
      <p className="font-mono text-sm text-ink-300">Completing sign-in…</p>
    </div>
  )
}
