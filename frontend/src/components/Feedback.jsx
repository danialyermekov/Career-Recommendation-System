import { useState } from 'react'
import { useApp } from '../context/AppContext'
import { submitFeedback } from '../utils/api'

export default function Feedback({ sessionId }) {
  const { t } = useApp()
  const text = t.product
  const [rating, setRating] = useState('')
  const [type, setType] = useState('review')
  const [title, setTitle] = useState('')
  const [steps, setSteps] = useState('')
  const [consent, setConsent] = useState(false)
  const [publicSubmitted, setPublicSubmitted] = useState(false)
  const [message, setMessage] = useState('')
  const [status, setStatus] = useState('')
  const submit = async event => {
    event.preventDefault()
    if ((type === 'review' && !rating) || (type === 'feature' && (title.trim().length < 5 || message.trim().length < 10)) ||
        (type === 'bug' && (!title.trim() || !message.trim()))) { setStatus('error'); return }
    setStatus('loading')
    try {
      await submitFeedback({ type, rating: type === 'review' ? Number(rating) : null,
        title: type === 'review' ? null : title.trim(), message: message.trim(),
        reproduction_steps: type === 'bug' ? steps.trim() : '', public_consent: type !== 'bug' && consent,
        session_id: sessionId || null, website: new FormData(event.target).get('website') || '' })
      setPublicSubmitted(type !== 'bug' && consent)
      setStatus('success'); setMessage(''); setRating(''); setTitle(''); setSteps(''); setConsent(false)
    } catch { setStatus('error') }
  }
  return <section className="betaCard" aria-label={text.feedback}>
    <h2>{text.shareFeedback}</h2>
    <form onSubmit={submit}>
      <label>{text.type}<select value={type} onChange={e => { setType(e.target.value); setRating(''); setTitle(''); setMessage(''); setSteps(''); setConsent(false); setStatus('') }}>
        {['review', 'feature', 'bug'].map(key => <option key={key} value={key}>{text[key]}</option>)}
      </select></label>
      {type === 'review' ? <label>{text.rating}<select required value={rating} onChange={e => setRating(e.target.value)}>
        <option value="">{text.chooseRating}</option>{[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n} {'★'.repeat(n)}</option>)}
      </select></label> : <label>{type === 'feature' ? text.featureTitle : text.title}<input required minLength={type === 'feature' ? 5 : 1} maxLength={120} value={title} onChange={e => setTitle(e.target.value)} /></label>}
      <label>{type === 'review' ? text.comment : type === 'feature' ? text.featureDescription : text.description}
        <textarea required={type !== 'review'} minLength={type === 'feature' ? 10 : undefined} maxLength={2000} value={message} onChange={e => setMessage(e.target.value)} />
      </label>
      {type === 'bug' && <label>{text.steps}<textarea maxLength={2000} value={steps} onChange={e => setSteps(e.target.value)} /></label>}
      {type !== 'bug' && <label className="consentField"><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} />{text.consent}</label>}
      <p>{text.moderationNote}</p>
      <p><a href="/privacy">{t.beta.privacy}</a> · <a href="/terms">{t.beta.terms}</a></p>
      <input name="website" type="text" hidden tabIndex={-1} autoComplete="off" />
      <button type="submit" disabled={status === 'loading'}>{status === 'loading' ? t.beta.loading : text.submit}</button>
      {status === 'success' && <p role="status">{text.thanks}{publicSubmitted && <> {text.pendingNote}</>}</p>}
      {status === 'error' && <p role="alert">{text.submitError}</p>}
    </form>
  </section>
}
