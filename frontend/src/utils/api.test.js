import * as api from './api'
import { clearLLMSettings, getLLMSettings, saveLLMSettings } from './llmSettings'
import * as authUtils from './supabase'
import { rememberDemoSession } from './demoProfile'

beforeEach(() => {
  clearLLMSettings()
  sessionStorage.clear()
  saveLLMSettings('anthropic', 'test-only-secret')
  global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({}) })
})
afterEach(() => { delete global.fetch })

test('free preview uses cookies and bounded history, without BYOK or server key headers', async () => {
  await api.sendTrialMessage('session', Array.from({ length: 8 }, () => ({ role: 'user', content: 'x'.repeat(1200) })), 'Career question', 'en')
  const [url, options] = fetch.mock.calls[0]
  expect(url).toContain('/ai/preview')
  expect(options.credentials).toBe('include')
  expect(options.headers['X-LLM-API-Key']).toBeUndefined()
  expect(options.headers['X-LLM-Provider']).toBeUndefined()
  const body = JSON.parse(options.body)
  expect(body.history).toHaveLength(4)
  expect(body.history[0].content).toHaveLength(1000)
  expect(body.consent).toBe(true)
  expect(options.body).not.toContain('test-only-secret')
})

test('demo calls stay guest-owned while the preview quota follows verified auth', async () => {
  const auth = jest.spyOn(authUtils, 'getAuthHeaders').mockResolvedValue({ Authorization: 'Bearer verified-test-user' })
  try {
    await api.getRecommendation({}, { demo: true })
    expect(fetch.mock.calls[0][1].headers.Authorization).toBeUndefined()
    expect(fetch.mock.calls[0][1].headers['X-Guest-Token']).toBeTruthy()
    rememberDemoSession('demo-session')
    await api.saveRoadmapProgress('demo-session', {})
    expect(fetch.mock.calls[1][1].headers.Authorization).toBeUndefined()
    await api.sendTrialMessage('demo-session', [], 'Career advice', 'en')
    expect(fetch.mock.calls[2][1].headers.Authorization).toBe('Bearer verified-test-user')
    expect(fetch.mock.calls[2][1].headers['X-Demo-Session']).toBe('true')
    expect(fetch.mock.calls[2][1].headers['X-Guest-Token']).toBeTruthy()
  } finally { auth.mockRestore() }
})

test.each([
  () => api.sendChat('session', [], 'Career question'),
  () => api.sendChatStream({ session_id: 'session', history: [], message: 'Career question' }),
  () => api.transcribeVoice(new Blob(['audio'], { type: 'audio/wav' }), 'en'),
])('AI calls send credentials only in headers', async call => {
  await call()
  const [url, options] = fetch.mock.calls[0]
  expect(options.headers['X-LLM-Provider']).toBe('anthropic')
  expect(options.headers['X-LLM-API-Key']).toBe('test-only-secret')
  expect(url).not.toContain('test-only-secret')
  expect(String(options.body)).not.toContain('test-only-secret')
})

test.each([
  () => api.getRecommendation({ skills: ['python'] }),
  () => api.parseResume({ name: 'resume.txt', type: 'text/plain', arrayBuffer: async () => new ArrayBuffer(0) }),
  () => api.getRecommendationHistory(),
  () => api.clearRecommendationHistory(),
  () => api.getRecommendationState('session'),
  () => api.saveRoadmapProgress('session', { doneSkills: [] }),
  () => api.saveCourseFilterPreferences('session', {}),
  () => api.filterCourses(['sql'], {}),
])('unrelated calls never send LLM credentials', async call => {
  await call()
  expect(JSON.stringify(fetch.mock.calls)).not.toContain('test-only-secret')
  expect(fetch.mock.calls[0][1]?.headers?.['X-LLM-Provider']).toBeUndefined()
})

test('missing credentials prevent an AI request but do not block recommendations', async () => {
  clearLLMSettings()
  await expect(api.sendChat('session', [], 'Question')).rejects.toMatchObject({ code: 'key_missing' })
  expect(fetch).not.toHaveBeenCalled()
  await api.getRecommendation({})
  expect(fetch).toHaveBeenCalledTimes(1)
})

test('provider errors keep the in-memory key and hide arbitrary response text', async () => {
  fetch.mockResolvedValue({ ok: false, json: async () => ({ detail: { code: 'key_rejected', message: 'test-only-secret' } }) })
  await expect(api.sendChat('session', [], 'Question')).rejects.toMatchObject({ code: 'key_rejected', message: 'AI request failed.' })
  expect(getLLMSettings().apiKey).toBe('test-only-secret')
})

test('stream payload serializes only conversation fields', async () => {
  await api.sendChatStream({ session_id: 'session', history: [{ role: 'user', content: 'Question', apiKey: 'test-only-secret' }], message: 'Question', apiKey: 'test-only-secret' })
  const body = JSON.parse(fetch.mock.calls[0][1].body)
  expect(body).toEqual({ session_id: 'session', history: [{ role: 'user', content: 'Question' }], message: 'Question' })
})

test('production uses the same origin on custom ports and preserves an explicit API URL', async () => {
  const location = window.location
  const nodeEnv = process.env.NODE_ENV
  const apiUrl = process.env.REACT_APP_API_URL
  Object.defineProperty(window, 'location', { configurable: true, value: { hostname: '127.0.0.1', port: '18000' } })
  try {
    for (const [mode, configured, expected] of [
      ['production', '', '/recommend'], ['development', '', 'http://localhost:8000/recommend'],
      ['production', 'https://api.example.test', 'https://api.example.test/recommend'],
    ]) {
      process.env.NODE_ENV = mode
      process.env.REACT_APP_API_URL = configured
      let client
      jest.isolateModules(() => { client = require('./api') })
      await client.getRecommendation({})
      expect(fetch.mock.calls.at(-1)[0]).toBe(expected)
    }
  } finally {
    Object.defineProperty(window, 'location', { configurable: true, value: location })
    process.env.NODE_ENV = nodeEnv
    if (apiUrl === undefined) delete process.env.REACT_APP_API_URL
    else process.env.REACT_APP_API_URL = apiUrl
  }
})
