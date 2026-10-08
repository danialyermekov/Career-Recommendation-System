import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useApp } from '../context/AppContext'

const slots = ['recommendation', 'explanation', 'comparison', 'roadmap', 'continue']

export default function GuidedTour({ step, onStep, onClose, onAdvisor, location }) {
  const { t } = useApp()
  const text = t.experience
  const [anchor, setAnchor] = useState(null)
  const card = useRef(null)
  useEffect(() => {
    const slot = document.querySelector(`[data-tour-slot="${slots[step]}"]`) || document.querySelector('[data-tour-slot="continue"]')
    setAnchor(slot)
    const target = slot?.nextElementSibling
    target?.setAttribute('data-tour-highlight', 'true')
    const details = step === 1 ? [...document.querySelectorAll('[data-tour-detail="explanation"]')] : []
    details.forEach(element => element.setAttribute('data-tour-highlight', 'true'))
    slot?.scrollIntoView({ behavior: 'auto', block: 'start' })
    return () => { target?.removeAttribute('data-tour-highlight'); details.forEach(element => element.removeAttribute('data-tour-highlight')) }
  }, [step, location])
  useEffect(() => { card.current?.focus() }, [anchor, step])
  if (!anchor) return null
  return createPortal(<aside className="guidedTour" ref={card} tabIndex={-1} aria-label={text.tour}
    onKeyDown={event => { if (event.key === 'Escape') onClose() }}>
    <span>{step + 1} / 5</span><h2>{text.steps[step][0]}</h2><p>{text.steps[step][1]}</p>
    {step === 4 && <><p>{text.temporary}</p><div className="tourControls"><a href="/#login">{text.login}</a><button onClick={() => { onClose(); onAdvisor() }}>{text.advisor}</button></div></>}
    <div className="tourControls"><button disabled={step === 0} onClick={() => onStep(step - 1)}>{text.back}</button>
      <button onClick={() => step === 4 ? onClose() : onStep(step + 1)}>{step === 4 ? text.finish : text.next}</button>
      <button onClick={onClose}>{text.skip}</button></div>
  </aside>, anchor)
}
