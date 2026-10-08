import { createContext, useContext, useEffect, useState } from 'react'
import { supabase, completeOAuthCallback, clearPrivateBrowserState, getOAuthRedirectUrl } from '../utils/supabase'
import { clearLLMSettings } from '../utils/llmSettings'

const AuthContext = createContext({ user: null, loading: false })
export const useAuth = () => useContext(AuthContext)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(supabase))
  const [error, setError] = useState(false)
  useEffect(() => {
    let active = true
    const update = session => { if (active) { setUser(session?.user || null); setLoading(false) } }
    // Remove legacy shared history without displaying it to a new account.
    clearPrivateBrowserState({ guest: false })
    if (!supabase) return () => { active = false }
    completeOAuthCallback()
      .then(() => supabase.auth.getSession())
      .then(({ data, error }) => { if (error) throw error; update(data.session) })
      .catch(() => { if (active) { setError(true); setLoading(false) } })
    const { data } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_OUT') { clearPrivateBrowserState(); clearLLMSettings() }
      if (active) setUser(session?.user || null)
    })
    return () => { active = false; data.subscription.unsubscribe() }
  }, [])

  const signIn = async provider => {
    setError(false)
    if (!supabase) { setError(true); return }
    if (!sessionStorage.getItem('careerflow-auth-return')) sessionStorage.setItem('careerflow-auth-return', window.location.hash === '#login' ? '#account' : window.location.hash || window.location.pathname)
    const { error } = await supabase.auth.signInWithOAuth({ provider, options: {
      redirectTo: getOAuthRedirectUrl(),
      scopes: provider === 'google' ? 'openid email profile' : 'read:user user:email',
    } })
    if (error) setError(true)
  }
  const signOut = async () => {
    const { error } = await supabase.auth.signOut()
    if (error) { setError(true); return }
    clearPrivateBrowserState()
    setUser(null)
    window.location.hash = ''
  }
  return <AuthContext.Provider value={{ user, loading, error, signIn, signOut, configured: Boolean(supabase) }}>{children}</AuthContext.Provider>
}
