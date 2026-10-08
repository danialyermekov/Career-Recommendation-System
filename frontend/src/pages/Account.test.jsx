import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { AppProvider } from '../context/AppContext'
import { AuthProvider, useAuth } from '../context/AuthContext'
import { translations } from '../i18n'
import { Login } from './Account'

jest.mock('../utils/supabase', () => {
  const actual = jest.requireActual('../utils/supabase')
  return {
    ...actual,
    supabase: { auth: { getSession: jest.fn(), onAuthStateChange: jest.fn(), signInWithOAuth: jest.fn(), signOut: jest.fn() } },
    completeOAuthCallback: jest.fn(),
    clearPrivateBrowserState: jest.fn(),
  }
})

let container, root
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true
  const { supabase, completeOAuthCallback } = require('../utils/supabase')
  supabase.auth.getSession.mockResolvedValue({ data: { session: null } })
  completeOAuthCallback.mockResolvedValue(null)
  supabase.auth.onAuthStateChange.mockReturnValue({ data: { subscription: { unsubscribe: jest.fn() } } })
  supabase.auth.signInWithOAuth.mockResolvedValue({ error: null })
  container = document.createElement('div')
  document.body.appendChild(container)
  root = createRoot(container)
})

afterEach(() => {
  act(() => root.unmount())
  container.remove()
  jest.clearAllMocks()
})

test.each(['en', 'ru', 'kk'])('Login page renders brand logo, title, buttons with icons, divider, and guest link in %s', async lang => {
  const t = translations[lang].beta
  await act(async () => {
    root.render(
      <AppProvider initialLanguage={lang}>
        <AuthProvider>
          <Login />
        </AuthProvider>
      </AppProvider>
    )
  })

  expect(container.querySelector('.loginBrand img[alt="CareerFlow"]')).not.toBeNull()
  expect(container.querySelector('h1').textContent).toBe(t.welcome)
  expect(container.querySelector('.loginSubtitle').textContent).toBe(t.loginSubtitle)

  const googleBtn = container.querySelector('.loginGoogleBtn')
  const githubBtn = container.querySelector('.loginGithubBtn')
  expect(googleBtn).not.toBeNull()
  expect(githubBtn).not.toBeNull()
  expect(googleBtn.textContent).toContain(t.google)
  expect(githubBtn.textContent).toContain(t.github)
  expect(googleBtn.querySelector('svg')).not.toBeNull()
  expect(githubBtn.querySelector('svg')).not.toBeNull()

  const guestBtn = container.querySelector('.loginGuestBtn')
  expect(guestBtn).not.toBeNull()
  expect(guestBtn.getAttribute('href')).toBe('#profile')
  expect(guestBtn.textContent).toBe(t.guest)

  expect(container.querySelector('.loginGuestMuted').textContent).toBe(t.guestShortNote)
  expect(container.querySelector('.loginDivider').textContent).toBe(t.or)
})

test('Google and GitHub buttons trigger OAuth sign-in with correct provider', async () => {
  const { supabase } = require('../utils/supabase')
  await act(async () => {
    root.render(
      <AppProvider initialLanguage="en">
        <AuthProvider>
          <Login />
        </AuthProvider>
      </AppProvider>
    )
  })

  const googleBtn = container.querySelector('.loginGoogleBtn')
  const githubBtn = container.querySelector('.loginGithubBtn')

  await act(async () => googleBtn.click())
  expect(supabase.auth.signInWithOAuth).toHaveBeenCalledWith(
    expect.objectContaining({ provider: 'google' })
  )

  await act(async () => githubBtn.click())
  expect(supabase.auth.signInWithOAuth).toHaveBeenCalledWith(
    expect.objectContaining({ provider: 'github' })
  )
})
