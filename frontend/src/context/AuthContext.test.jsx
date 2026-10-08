import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { AuthProvider, useAuth } from './AuthContext'
import { supabase, completeOAuthCallback } from '../utils/supabase'

jest.mock('../utils/supabase', () => {
  const actual = jest.requireActual('../utils/supabase')
  return {
    ...actual,
    supabase: { auth: { getSession: jest.fn(), onAuthStateChange: jest.fn(), signInWithOAuth: jest.fn(), signOut: jest.fn() } },
    completeOAuthCallback: jest.fn(),
    clearPrivateBrowserState: jest.fn(),
  }
})
let container, root, context, listener
function Probe() { context = useAuth(); return <p>{context.user?.id || 'guest'}</p> }
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true
  window.history.replaceState({}, '', '/#login'); sessionStorage.clear()
  supabase.auth.getSession.mockResolvedValue({ data: { session: null } })
  completeOAuthCallback.mockResolvedValue(null)
  supabase.auth.onAuthStateChange.mockImplementation(callback => { listener = callback; return { data: { subscription: { unsubscribe: jest.fn() } } } })
  supabase.auth.signInWithOAuth.mockResolvedValue({ error: null })
  supabase.auth.signOut.mockResolvedValue({ error: null })
  container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container)
})
afterEach(() => { act(() => root.unmount()); container.remove(); jest.clearAllMocks() })

test('guest, authenticated, refreshed and signed-out states follow Supabase events', async () => {
  await act(async () => root.render(<AuthProvider><Probe /></AuthProvider>))
  expect(context.loading).toBe(false); expect(context.user).toBeNull()
  act(() => listener('SIGNED_IN', { user: { id: 'user-a' } }))
  expect(container.textContent).toBe('user-a')
  act(() => listener('TOKEN_REFRESHED', { user: { id: 'user-a' } }))
  expect(context.user.id).toBe('user-a')
  act(() => listener('SIGNED_OUT', null))
  expect(container.textContent).toBe('guest')
})

test('OAuth uses the same-origin callback and minimal identity scopes', async () => {
  await act(async () => root.render(<AuthProvider><Probe /></AuthProvider>))
  await act(async () => context.signIn('google'))
  expect(supabase.auth.signInWithOAuth).toHaveBeenLastCalledWith({ provider: 'google', options: { redirectTo: `${window.location.origin}/auth/callback`, scopes: 'openid email profile' } })
  await act(async () => context.signIn('github'))
  expect(supabase.auth.signInWithOAuth.mock.calls[1][0].options.scopes).toBe('read:user user:email')
})

test('OAuth errors surface without echoing provider details', async () => {
  supabase.auth.signInWithOAuth.mockResolvedValue({ error: { message: 'private-detail' } })
  await act(async () => root.render(<AuthProvider><Probe /></AuthProvider>))
  await act(async () => context.signIn('google'))
  expect(context.error).toBe(true)
  expect(container.textContent).not.toContain('private-detail')
})
