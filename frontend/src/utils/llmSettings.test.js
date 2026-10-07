import { clearLLMSettings, getLLMHeaders, getLLMSettings, saveLLMSettings } from './llmSettings'

beforeEach(() => { clearLLMSettings(); sessionStorage.clear(); localStorage.clear() })

test('keeps credentials only in memory and removes them immediately', () => {
  const write = jest.spyOn(Storage.prototype, 'setItem')
  expect(getLLMSettings()).toBeNull()
  saveLLMSettings('anthropic', ' test-only-secret ')
  expect(getLLMSettings()).toEqual({ provider: 'anthropic', apiKey: 'test-only-secret' })
  expect(getLLMHeaders()).toEqual({ 'X-LLM-Provider': 'anthropic', 'X-LLM-API-Key': 'test-only-secret' })
  expect(localStorage.length).toBe(0)
  expect(sessionStorage.length).toBe(0)
  expect(write).not.toHaveBeenCalled()
  write.mockRestore()
  clearLLMSettings()
  expect(getLLMSettings()).toBeNull()
  expect(sessionStorage.length).toBe(0)
  expect(() => getLLMHeaders()).toThrow('Add an API key')
})

test('a fresh application starts empty and deletes legacy entries without reading them', () => {
  saveLLMSettings('gemini', 'test-only-secret')
  for (const storage of [localStorage, sessionStorage]) {
    storage.setItem('careerflow-llm-session', JSON.stringify({ provider: 'gemini', apiKey: 'old-test-secret' }))
    storage.setItem('unrelated-preference', 'keep')
  }
  const read = jest.spyOn(Storage.prototype, 'getItem')
  jest.isolateModules(() => {
    const fresh = require('./llmSettings')
    expect(fresh.getLLMSettings()).toBeNull()
    expect(() => fresh.getLLMHeaders()).toThrow('Add an API key')
    expect(read).not.toHaveBeenCalled()
  })
  read.mockRestore()
  for (const storage of [localStorage, sessionStorage]) {
    expect(storage.getItem('careerflow-llm-session')).toBeNull()
    expect(storage.getItem('unrelated-preference')).toBe('keep')
  }
})

test('AI credentials work when browser storage is unavailable', () => {
  const remove = jest.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => { throw new Error('Storage blocked') })
  const write = jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Storage blocked') })
  try {
    jest.isolateModules(() => {
      const fresh = require('./llmSettings')
      fresh.saveLLMSettings('gemini', 'test-only-secret')
      expect(fresh.getLLMHeaders()['X-LLM-API-Key']).toBe('test-only-secret')
      fresh.clearLLMSettings()
      expect(fresh.getLLMSettings()).toBeNull()
      expect(write).not.toHaveBeenCalled()
    })
  } finally {
    remove.mockRestore()
    write.mockRestore()
  }
})

test('rejects unsupported providers and invalid key formats', () => {
  expect(() => saveLLMSettings('other', 'test-key')).toThrow('key_invalid')
  expect(() => saveLLMSettings('gemini', 'test\nkey')).toThrow('key_invalid')
  expect(() => saveLLMSettings('gemini', '')).toThrow('key_invalid')
  expect(getLLMSettings()).toBeNull()
})

test('does not put secrets in settings change notifications', () => {
  const listener = jest.fn()
  window.addEventListener('careerflow-llm-settings-changed', listener)
  saveLLMSettings('gemini', 'test-only-secret')
  expect(listener).toHaveBeenCalledTimes(1)
  expect(listener.mock.calls[0][0].detail).toBeUndefined()
  window.removeEventListener('careerflow-llm-settings-changed', listener)
})
