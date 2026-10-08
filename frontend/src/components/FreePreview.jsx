import { useEffect, useState } from 'react'
import { useApp } from '../context/AppContext'
import { getTrialStatus, sendTrialMessage } from '../utils/api'

export default function FreePreview({ sessionId }) {
  const { t, lang } = useApp()
  const text = t.experience
  const [quota, setQuota] = useState(null)
  const [consent, setConsent] = useState(() => {
    if (typeof window === 'undefined' || process.env.NODE_ENV === 'test') return false
    try {
      return sessionStorage.getItem('careerflow-ai-consent') === 'true'
    } catch {
      return false
    }
  })
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    getTrialStatus().then(value => { if (active) setQuota(value) }).catch(() => { if (active) setError('unavailable') })
    return () => { active = false }
  }, [sessionId])

  const handleConsentChange = event => {
    const checked = event.target.checked
    setConsent(checked)
    try {
      sessionStorage.setItem('careerflow-ai-consent', String(checked))
    } catch {}
  }

  const send = async question => {
    const message = (question ?? input).trim()
    if (!consent || busy || !quota?.available || !quota.remaining || !message || message.length > 1000) return
    setBusy(true); setError('')
    try {
      const reply = await sendTrialMessage(sessionId, messages, message, lang)
      setMessages(previous => [...previous, { role: 'user', content: message }, { role: 'assistant', content: reply.response }])
      setQuota(previous => ({ ...previous, remaining: reply.remaining }))
      setInput('')
    } catch (failure) {
      setError(failure.code === 'trial_exhausted' ? 'exhausted' : ['trial_busy', 'trial_rate_limited'].includes(failure.code) ? 'busy' : failure.code === 'trial_provider_failed' ? 'failed' : 'unavailable')
      try { setQuota(await getTrialStatus()) } catch { setQuota(null) }
    } finally { setBusy(false) }
  }

  const enabled = quota?.available && quota.remaining > 0 && consent && !busy

  return (
    <section className="freePreview" aria-label={text.free}>
      <div className="previewHeader">
        <h3>{text.free}</h3>
        <p className="previewSubtitle">{text.freeText}</p>
        {quota && <p className="previewQuota" role="status">{text.remaining(quota.remaining, quota.total)}</p>}
        {!quota && !error && <p className="previewStatus" role="status">{t.beta.loading}</p>}
        {(quota?.available === false || error === 'unavailable') && <p className="previewStatus previewUnavailable" role="status">{text.unavailable}</p>}
        {quota?.available && quota.remaining === 0 && <p className="previewStatus previewExhausted">{text.exhausted}</p>}
      </div>

      <div className="previewMessages" aria-live="polite">
        {messages.map((message, index) => (
          <div key={index} className={`previewMessage ${message.role === 'assistant' ? 'previewAssistant' : 'previewUser'}`}>
            <p>
              {message.role === 'assistant' && <strong>Gemini: </strong>}
              {message.content}
            </p>
          </div>
        ))}
      </div>

      {error && error !== 'unavailable' && (
        <p className="previewAlert" role="alert">{text[error] || text.failed}</p>
      )}

      <div className="previewSuggestions" aria-label="Suggested questions">
        {text.suggestions.map(question => (
          <button
            key={question}
            type="button"
            className="suggestionChip"
            disabled={!enabled}
            onClick={() => send(question)}
          >
            {question}
          </button>
        ))}
      </div>

      <form className="previewForm" onSubmit={event => { event.preventDefault(); send() }}>
        <label className="previewConsentCompact">
          <input
            type="checkbox"
            checked={consent}
            onChange={handleConsentChange}
          />
          <span>{text.ageConfirm}</span>
        </label>

        <div className="previewInputWrapper">
          <textarea
            aria-label={t.results.chatPlaceholder}
            maxLength={1000}
            value={input}
            onChange={event => setInput(event.target.value)}
            disabled={!enabled}
            rows={2}
            placeholder={t.results.chatPlaceholder}
            onKeyDown={event => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                send()
              }
            }}
          />
          <button type="submit" className="previewSendButton" disabled={!enabled || !input.trim()}>
            {busy ? t.beta.loading : t.results.chatSend}
          </button>
        </div>

        <p className="previewDisclosure">
          {text.disclosure} <a href="/privacy">{text.privacyLink}</a>
        </p>
      </form>
    </section>
  )
}
