const mockAuth = {
  getSession: jest.fn(), exchangeCodeForSession: jest.fn(),
}
jest.mock('@supabase/supabase-js', () => ({ createClient: jest.fn(() => ({ auth: mockAuth })) }))

let originalUrl, originalKey
beforeEach(() => {
  jest.resetModules(); jest.clearAllMocks()
  originalUrl = process.env.REACT_APP_SUPABASE_URL; originalKey = process.env.REACT_APP_SUPABASE_PUBLISHABLE_KEY
  process.env.REACT_APP_SUPABASE_URL = 'https://test.supabase.co'
  process.env.REACT_APP_SUPABASE_PUBLISHABLE_KEY = 'public-key'
  window.history.replaceState({}, '', '/')
  sessionStorage.clear(); localStorage.clear()
  mockAuth.getSession.mockResolvedValue({ data: { session: null } })
})
afterEach(() => {
  if (originalUrl === undefined) delete process.env.REACT_APP_SUPABASE_URL; else process.env.REACT_APP_SUPABASE_URL = originalUrl
  if (originalKey === undefined) delete process.env.REACT_APP_SUPABASE_PUBLISHABLE_KEY; else process.env.REACT_APP_SUPABASE_PUBLISHABLE_KEY = originalKey
})

test('PKCE callback exchanges once, removes code and restores an intended hash route', async () => {
  window.history.replaceState({}, '', '/?code=one-use-code&sb_flow_id=flow')
  sessionStorage.setItem('careerflow-auth-return', '#results/owned-session')
  mockAuth.exchangeCodeForSession.mockResolvedValue({ data: { session: { access_token: 'test-token' } } })
  const { completeOAuthCallback } = require('./supabase')
  await Promise.all([completeOAuthCallback(), completeOAuthCallback()])
  expect(mockAuth.exchangeCodeForSession).toHaveBeenCalledTimes(1)
  expect(mockAuth.exchangeCodeForSession).toHaveBeenCalledWith('one-use-code', { flowId: 'flow' })
  expect(window.location.search).toBe('')
  expect(window.location.hash).toBe('#results/owned-session')
})

test('callback errors are cleaned up and cannot redirect outside known hash routes', async () => {
  window.history.replaceState({}, '', '/?error=access_denied&error_description=private-detail')
  sessionStorage.setItem('careerflow-auth-return', 'https://attacker.example')
  const { completeOAuthCallback } = require('./supabase')
  await expect(completeOAuthCallback()).rejects.toThrow('OAuth failed')
  expect(window.location.search).toBe('')
  expect(window.location.hash).toBe('#account')
  expect(mockAuth.exchangeCodeForSession).not.toHaveBeenCalled()
})

test('OAuth restores a permitted public path and strips callback query data', async () => {
  window.history.replaceState({}, '', '/?code=public-return')
  sessionStorage.setItem('careerflow-auth-return', '/feedback')
  mockAuth.exchangeCodeForSession.mockResolvedValue({ data: { session: { access_token: 'test-token' } } })
  const { completeOAuthCallback } = require('./supabase')
  await completeOAuthCallback()
  expect(window.location.pathname).toBe('/feedback')
  expect(window.location.search).toBe('')
})

test('access token is sent only as an authorization header, guests receive a random tab credential', async () => {
  const { getAuthHeaders, clearPrivateBrowserState } = require('./supabase')
  const first = await getAuthHeaders()
  expect(first['X-Guest-Token']).toMatch(/^[0-9a-f]{64}$/)
  expect(await getAuthHeaders()).toEqual(first)
  clearPrivateBrowserState()
  expect(await getAuthHeaders()).not.toEqual(first)
  mockAuth.getSession.mockResolvedValue({ data: { session: { access_token: 'test-token' } } })
  expect(await getAuthHeaders()).toEqual({ Authorization: 'Bearer test-token' })
  expect(window.location.href).not.toContain('test-token')
})

test('sign-out cleanup removes legacy private data and preserves display preferences', () => {
  const { clearPrivateBrowserState } = require('./supabase')
  localStorage.setItem('career-recommendation-history', 'private-data')
  localStorage.setItem('career-result:test', 'private-progress')
  localStorage.setItem('lang', 'ru')
  clearPrivateBrowserState()
  expect(localStorage.getItem('career-recommendation-history')).toBeNull()
  expect(localStorage.getItem('career-result:test')).toBeNull()
  expect(localStorage.getItem('lang')).toBe('ru')
})

test('SDK storage preserves Supabase sessions and PKCE but strips provider access/refresh tokens', () => {
  const { authStorage } = require('./supabase')
  authStorage.setItem('test-auth', JSON.stringify({ access_token: 'supabase-token', refresh_token: 'supabase-refresh', provider_token: 'google-secret', provider_refresh_token: 'github-secret' }))
  expect(JSON.parse(authStorage.getItem('test-auth'))).toEqual({ access_token: 'supabase-token', refresh_token: 'supabase-refresh' })
  expect(authStorage.getItem('test-auth')).not.toContain('secret')
  authStorage.setItem('test-verifier', 'plain-pkce-verifier')
  expect(authStorage.getItem('test-verifier')).toBe('plain-pkce-verifier')
  authStorage.removeItem('test-auth')
  expect(authStorage.getItem('test-auth')).toBeNull()
})

test('getOAuthRedirectUrl creates trusted /auth/callback URLs for local and production origins', () => {
  const { getOAuthRedirectUrl } = require('./supabase')
  expect(getOAuthRedirectUrl('http://localhost:8000')).toBe('http://localhost:8000/auth/callback')
  expect(getOAuthRedirectUrl('http://localhost:3000')).toBe('http://localhost:3000/auth/callback')
  expect(getOAuthRedirectUrl('http://localhost:18011')).toBe('http://localhost:18011/auth/callback')
  expect(getOAuthRedirectUrl('http://127.0.0.1:8000')).toBe('http://127.0.0.1:8000/auth/callback')
  expect(getOAuthRedirectUrl('https://careerflow.live')).toBe('https://careerflow.live/auth/callback')
  expect(getOAuthRedirectUrl('https://www.careerflow.live')).toBe('https://www.careerflow.live/auth/callback')
  expect(getOAuthRedirectUrl('https://evil-attacker.example')).toBe('https://careerflow.live/auth/callback')
  expect(getOAuthRedirectUrl('')).toBe('https://careerflow.live/auth/callback')
})

