import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { LogIn } from 'lucide-react'
import AuthShell from '../components/AuthShell'
import { useAuth } from '../lib/auth'
import { ErrorNote, btnPrimary, inputCls } from '../components/ui'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const oauthError = searchParams.get('oauth_error')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(
    oauthError ? oauthError.replace(/_/g, ' ') : null,
  )
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell title="Welcome back" sub="Sign in to your trading terminal">
      <form onSubmit={submit} className="space-y-4">
        {error && <ErrorNote message={error} />}
        <div>
          <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
            Email
          </label>
          <input
            type="email"
            required
            autoComplete="email"
            className={inputCls}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="trader@alphaedge.io"
          />
        </div>
        <div>
          <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-widest text-ink-300">
            Password
          </label>
          <input
            type="password"
            required
            autoComplete="current-password"
            className={inputCls}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
        </div>
        <button type="submit" disabled={busy} className={`${btnPrimary} w-full`}>
          <LogIn size={16} />
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
        <div className="relative my-2">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-ink-700" />
          </div>
          <div className="relative flex justify-center">
            <span className="bg-ink-950 px-2 font-mono text-[10px] uppercase tracking-widest text-ink-400">
              or continue with
            </span>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <a
            href="/api/v1/auth/oauth/google"
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-ink-600 bg-ink-800/60 px-3 py-2 text-sm font-medium text-ink-100 transition hover:border-volt-500/40 hover:bg-ink-800"
          >
            Google
          </a>
          <a
            href="/api/v1/auth/oauth/github"
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-ink-600 bg-ink-800/60 px-3 py-2 text-sm font-medium text-ink-100 transition hover:border-volt-500/40 hover:bg-ink-800"
          >
            GitHub
          </a>
        </div>
      </form>
      <p className="mt-6 text-center text-sm text-ink-300">
        No account?{' '}
        <Link to="/register" className="font-medium text-volt-400 hover:text-volt-300">
          Open one free
        </Link>
      </p>
    </AuthShell>
  )
}
