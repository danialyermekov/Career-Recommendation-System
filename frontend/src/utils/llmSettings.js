export const LLM_PROVIDERS = [
  { id: 'anthropic', name: 'Claude / Anthropic', voice: false },
  { id: 'gemini', name: 'Gemini / Google', voice: true },
]

export const LLM_SETTINGS_EVENT = 'careerflow-llm-settings-changed'
let settings = null

// Remove credentials saved by earlier versions; never read or restore them.
try { sessionStorage.removeItem('careerflow-llm-session') } catch {}
try { localStorage.removeItem('careerflow-llm-session') } catch {}

export function getLLMSettings() {
  return settings ? { ...settings } : null
}

export function saveLLMSettings(provider, apiKey) {
  const key = apiKey.trim()
  if (!LLM_PROVIDERS.some(p => p.id === provider) || !/^[\x21-\x7e]{1,4096}$/.test(key)) {
    throw new Error('key_invalid')
  }
  settings = { provider, apiKey: key }
  window.dispatchEvent(new Event(LLM_SETTINGS_EVENT))
}

export function clearLLMSettings() {
  settings = null
  window.dispatchEvent(new Event(LLM_SETTINGS_EVENT))
}

export function getLLMHeaders() {
  const settings = getLLMSettings()
  if (!settings) throw Object.assign(new Error('Add an API key to enable the AI assistant.'), { code: 'key_missing' })
  return { 'X-LLM-Provider': settings.provider, 'X-LLM-API-Key': settings.apiKey }
}
