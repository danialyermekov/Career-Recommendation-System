import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useApp } from '../context/AppContext'
import { getRecommendationHistory, deleteAccount, clearRecommendationHistory } from '../utils/api'
import BrandLogo from '../components/BrandLogo'

function GoogleIcon() {
  return (
    <svg className="loginProviderIcon" width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
    </svg>
  )
}

function GithubIcon() {
  return (
    <svg className="loginProviderIcon" width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false">
      <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  )
}

export function Login() {
  const { t } = useApp()
  const { signIn, error, configured, loading } = useAuth()

  return (
    <main className="betaPage loginPage">
      <section className="loginCard" aria-label={t.beta.login}>
        <div className="loginBrand">
          <BrandLogo />
        </div>
        <h1 className="loginTitle">{t.beta.welcome}</h1>
        <p className="loginSubtitle">{t.beta.loginSubtitle}</p>

        <div className="loginOAuthGroup">
          <button
            type="button"
            className="loginBtn loginGoogleBtn"
            disabled={!configured || loading}
            onClick={() => signIn('google')}
            aria-label={t.beta.google}
          >
            <GoogleIcon />
            <span>{t.beta.google}</span>
          </button>

          <button
            type="button"
            className="loginBtn loginGithubBtn"
            disabled={!configured || loading}
            onClick={() => signIn('github')}
            aria-label={t.beta.github}
          >
            <GithubIcon />
            <span>{t.beta.github}</span>
          </button>
        </div>

        {(error || !configured) && (
          <div className="loginAlert" role="alert">
            <p>{t.beta.authError}</p>
          </div>
        )}

        <div className="loginDivider" role="separator">
          <span>{t.beta.or}</span>
        </div>

        <a href="#profile" className="loginGuestBtn">
          {t.beta.guest}
        </a>

        <p className="loginGuestMuted">{t.beta.guestShortNote}</p>
      </section>
    </main>
  )
}

export default function Account() {
  const { t } = useApp()
  const { user, signOut } = useAuth()
  const [items, setItems] = useState([])
  const [status, setStatus] = useState('loading')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    if (user) getRecommendationHistory().then(data => { if (active) { setItems(data.items); setStatus('ready') } }).catch(() => { if (active) setStatus('error') })
    return () => { active = false }
  }, [user])
  if (!user) return <Login />
  const remove = async () => {
    if (!window.confirm(t.beta.deleteConfirm)) return
    setBusy(true); setError('')
    try { await deleteAccount(); await signOut() } catch { setError(t.beta.deleteError) }
    finally { setBusy(false) }
  }
  const clear = async () => {
    if (!window.confirm(t.review.clearHistoryConfirm)) return
    try { await clearRecommendationHistory(); setItems([]) } catch { setError(t.beta.loadError) }
  }
  return <main className="betaPage"><section className="betaCard">
    <h1>{t.beta.account}</h1><p>{user.user_metadata?.full_name || user.user_metadata?.name || user.email}</p><p>{user.email}</p>
    <p>{t.beta.historyNote}</p>
    {status === 'loading' && <p role="status">{t.beta.loading}</p>}
    {status === 'error' && <p role="alert">{t.beta.loadError}</p>}
    {status === 'ready' && !items.length && <p>{t.beta.emptyHistory}</p>}
    <ul>{items.map(item => <li key={item.id}><a href={`#results/${item.results.session_id}`}>{t.professions[item.selectedProfession] || item.selectedProfession}</a>
      {' · '}{item.progress.done.length} {t.beta.savedProgress}</li>)}</ul>
    <div className="betaActions"><button onClick={signOut}>{t.beta.logout}</button>
      {items.length > 0 && <button onClick={clear}>{t.results.clearHistory}</button>}
      <button disabled={busy} onClick={remove}>{busy ? t.beta.loading : t.beta.deleteAccount}</button></div>
    {error && <p role="alert">{error}</p>}
  </section></main>
}
