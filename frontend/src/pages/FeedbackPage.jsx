import { useEffect, useRef, useState } from 'react'
import { useApp } from '../context/AppContext'
import { useAuth } from '../context/AuthContext'
import Feedback from '../components/Feedback'
import { getPublicFeedback, voteFeedback } from '../utils/api'

export default function FeedbackPage() {
  const { t, lang } = useApp()
  const { user } = useAuth()
  const text = t.product
  const [type, setType] = useState('review')
  const [items, setItems] = useState([])
  const [hasMore, setHasMore] = useState(false)
  const [status, setStatus] = useState('loading')
  const [revision, setRevision] = useState(0)
  const [busy, setBusy] = useState(null)
  const [voteError, setVoteError] = useState(false)
  const dialog = useRef(null)
  const currentType = useRef(type)
  currentType.current = type
  useEffect(() => {
    let active = true
    setStatus('loading'); setItems([]); setVoteError(false); setHasMore(false)
    getPublicFeedback(type).then(data => {
      if (active) { setItems(data.items); setHasMore(data.has_more); setStatus('ready') }
    }).catch(() => { if (active) setStatus('error') })
    return () => { active = false }
  }, [type, revision])
  const more = async () => {
    setBusy('more')
    try {
      const data = await getPublicFeedback(type, items.length)
      if (currentType.current === type) { setItems(previous => [...previous, ...data.items.filter(item => !previous.some(old => old.id === item.id))]); setHasMore(data.has_more) }
    } catch { setVoteError(true) }
    finally { setBusy(null) }
  }
  const vote = async item => {
    setBusy(item.id); setVoteError(false)
    try {
      const result = await voteFeedback(item.id, !item.voted)
      setItems(previous => previous.map(row => row.id === item.id ? { ...row, ...result } : row))
    } catch { setVoteError(true) }
    finally { setBusy(null) }
  }
  return <main className="betaPage productPage"><header className="publicHeading">
    <div><h1>{text.feedback}</h1><p>{text.feedbackSubtitle}</p></div>
    <button type="button" onClick={() => dialog.current.showModal()}>{text.shareFeedback}</button>
  </header>
    <div className="publicTabs" role="tablist" aria-label={text.feedback}>
      {['review', 'feature'].map(kind => <button type="button" role="tab" id={`tab-${kind}`} tabIndex={type === kind ? 0 : -1} aria-selected={type === kind} aria-controls="feedback-list" key={kind}
        onKeyDown={event => {
          if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
            event.preventDefault()
            const next = event.key === 'Home' ? 'review' : event.key === 'End' ? 'feature' : kind === 'review' ? 'feature' : 'review'
            setType(next); document.getElementById(`tab-${next}`).focus()
          }
        }}
        onClick={() => setType(kind)}>{kind === 'review' ? text.reviews : text.features}</button>)}
    </div>
    <section id="feedback-list" role="tabpanel" aria-labelledby={`tab-${type}`} aria-busy={status === 'loading'}>
      {status === 'loading' && <p role="status">{t.beta.loading}</p>}
      {status === 'error' && <p role="alert">{text.loadError} <button onClick={() => setRevision(value => value + 1)}>{text.retry}</button></p>}
      {status === 'ready' && !items.length && <p className="publicEmpty">{type === 'review' ? text.noReviews : text.noFeatures}</p>}
      <div className="feedbackGrid">{items.map(item => <article className="feedbackCard" key={item.id}>
        {item.type === 'review' ? <p className="reviewStars" aria-label={`${item.rating}/5`}>{'★'.repeat(item.rating)}{'☆'.repeat(5 - item.rating)}</p> : <h2>{item.title}</h2>}
        {item.message && <p className="feedbackMessage">{item.message}</p>}
        <div className="feedbackMeta"><span>{item.developer_feedback ? text.developer : text.anonymous}</span>
          <time dateTime={item.created_at}>{new Date(item.created_at).toLocaleDateString(lang === 'kk' ? 'kk-KZ' : lang)}</time></div>
        {item.type === 'feature' && <div className="featureActions"><span className="statusBadge">{text[item.development_status]}</span>
          <span>{item.votes} {text.votes}</span>
          {user ? <button type="button" disabled={busy !== null} aria-pressed={item.voted} onClick={() => vote(item)}>{item.voted ? text.unvote : text.vote}</button> :
            <a href="/#login" onClick={() => sessionStorage.setItem('careerflow-auth-return', '/feedback')}>{text.voteLogin}</a>}
        </div>}
      </article>)}</div>
      {voteError && <p role="alert">{text.voteError}</p>}
      {hasMore && <button disabled={busy !== null} onClick={more}>{text.more}</button>}
    </section>
    <p>{t.experience.contact} <a href="mailto:contact@careerflow.live">contact@careerflow.live</a></p>
    <dialog ref={dialog} className="feedbackDialog" aria-labelledby="feedback-dialog-title">
      <div className="dialogHeading"><h2 id="feedback-dialog-title">{text.shareFeedback}</h2><button type="button" onClick={() => dialog.current.close()}>{text.close}</button></div>
      <Feedback />
    </dialog>
  </main>
}
