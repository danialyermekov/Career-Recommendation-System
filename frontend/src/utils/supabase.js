import { createClient } from '@supabase/supabase-js'

const url = process.env.REACT_APP_SUPABASE_URL
const key = process.env.REACT_APP_SUPABASE_PUBLISHABLE_KEY
export const authStorage = {
  getItem: key => localStorage.getItem(key),
  removeItem: key => localStorage.removeItem(key),
  setItem: (key, value) => {
    let stored = value
    try {
      const session = JSON.parse(value)
      if (session && typeof session === 'object') {
        delete session.provider_token
        delete session.provider_refresh_token
        stored = JSON.stringify(session)
      }
    } catch { /* PKCE verifier values may be plain strings. */ }
    localStorage.setItem(key, stored)
  },
}
export const supabase = url && key ? createClient(url, key, {
  auth: { flowType: 'pkce', persistSession: true, autoRefreshToken: true, detectSessionInUrl: false, storage: authStorage },
}) : null

export function getTrustedOrigin(origin = (typeof window !== 'undefined' ? window.location.origin : '')) {
  if (!origin) return 'https://careerflow.live'
  try {
    const parsed = new URL(origin)
    const hostname = parsed.hostname
    if (
      (parsed.protocol === 'http:' || parsed.protocol === 'https:') &&
      (hostname === 'localhost' || hostname === '127.0.0.1')
    ) {
      return parsed.origin
    }
    if (parsed.protocol === 'https:' && (hostname === 'careerflow.live' || hostname === 'www.careerflow.live')) {
      return parsed.origin
    }
  } catch {}
  return 'https://careerflow.live'
}

export function getOAuthRedirectUrl(origin) {
  return `${getTrustedOrigin(origin)}/auth/callback`
}

let guestToken
export async function getAuthHeaders() {
  if (supabase) {
    const { data, error } = await supabase.auth.getSession()
    if (error) throw new Error('Authentication unavailable')
    if (data.session) return { Authorization: `Bearer ${data.session.access_token}` }
  }
  return getGuestHeaders()
}

export function getGuestHeaders() {
  if (!guestToken) {
    guestToken = sessionStorage.getItem('careerflow-guest-token')
    if (!guestToken) {
      guestToken = Array.from(crypto.getRandomValues(new Uint8Array(32)), n => n.toString(16).padStart(2, '0')).join('')
      sessionStorage.setItem('careerflow-guest-token', guestToken)
    }
  }
  return { 'X-Guest-Token': guestToken }
}

export function clearPrivateBrowserState({ guest = true } = {}) {
  for (const storage of [localStorage, sessionStorage]) {
    for (const key of Object.keys(storage)) {
      if (key.startsWith('career-result:') || key.startsWith('career-recommendation-') || (guest && key === 'careerflow-guest-token')) storage.removeItem(key)
    }
  }
  if (guest) guestToken = null
}

let callbackPromise
export function completeOAuthCallback() {
  const params = new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '')
  if (!params.has('code') && !params.has('error')) {
    if (typeof window !== 'undefined' && window.location.pathname === '/auth/callback') {
      window.history.replaceState({}, '', '/#login')
    }
    return Promise.resolve(null)
  }
  if (!callbackPromise) {
    callbackPromise = (async () => {
      try {
        if (params.has('error') || !supabase) throw new Error('OAuth failed')
        const flowId = params.get('sb_flow_id')
        const { data, error } = await supabase.auth.exchangeCodeForSession(params.get('code'), flowId ? { flowId } : undefined)
        if (error) throw error
        return data.session
      } finally {
        const intended = sessionStorage.getItem('careerflow-auth-return') || '#account'
        sessionStorage.removeItem('careerflow-auth-return')
        const destination = /^#(profile|account|results\/[a-zA-Z0-9-]+)$/.test(intended) ? `/${intended}` :
          /^\/(feedback|about|changelog|roadmap|privacy|terms|contact|disclaimer)$/.test(intended) ? intended : '/#account'
        window.history.replaceState({}, '', destination)
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new PopStateEvent('popstate'))
        }
      }
    })()
  }
  return callbackPromise
}
