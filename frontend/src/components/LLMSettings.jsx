import { useEffect, useRef, useState } from 'react'
import { useApp } from '../context/AppContext'
import { clearLLMSettings, LLM_PROVIDERS, saveLLMSettings } from '../utils/llmSettings'
import styles from './LLMSettings.module.css'

export default function LLMSettings() {
  const { t, llmProvider } = useApp()
  const [provider, setProvider] = useState(llmProvider || LLM_PROVIDERS[0].id)
  const [error, setError] = useState('')
  const inputRef = useRef(null)
  useEffect(() => { setProvider(llmProvider || LLM_PROVIDERS[0].id) }, [llmProvider])

  const save = event => {
    event.preventDefault()
    try {
      saveLLMSettings(provider, inputRef.current.value)
      inputRef.current.value = ''
      setError('')
    } catch (err) {
      setError(t.llm.errors[err.message] || t.llm.errors.key_invalid)
    }
  }
  const remove = () => {
    clearLLMSettings()
    inputRef.current.value = ''
    setError('')
  }

  return (
    <section className={styles.settings} aria-label={t.llm.configure}>
      {llmProvider && <div className={styles.status}>
        <span role="status">{LLM_PROVIDERS.find(p => p.id === llmProvider)?.name} · •••••••• {t.llm.configured}</span>
        <button type="button" onClick={remove}>{t.llm.remove}</button>
      </div>}
      <details open={!llmProvider}>
        <summary>{llmProvider ? t.llm.change : t.llm.configure}</summary>
        <form onSubmit={save} autoComplete="off">
          <label htmlFor="llm-provider">{t.llm.provider}</label>
          <select id="llm-provider" value={provider} onChange={event => setProvider(event.target.value)}>
            {LLM_PROVIDERS.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <label htmlFor="llm-api-key">{t.llm.apiKey}</label>
          <input id="llm-api-key" ref={inputRef} type="password" required maxLength={4096}
            autoComplete="off" spellCheck={false} autoCapitalize="none" />
          <button type="submit">{t.llm.save}</button>
        </form>
      </details>
      <p>{t.llm.sessionOnly}</p>
      {error && <p role="alert">{error}</p>}
    </section>
  )
}
