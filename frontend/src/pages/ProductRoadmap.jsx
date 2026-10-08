import { useEffect, useState } from 'react'
import { useApp } from '../context/AppContext'
import { productRoadmap } from '../data/productUpdates'
import { getPublicRoadmap } from '../utils/api'

export default function ProductRoadmap() {
  const { t } = useApp()
  const text = t.product
  const [ideas, setIdeas] = useState([])
  const [status, setStatus] = useState('loading')
  useEffect(() => {
    let active = true
    getPublicRoadmap().then(data => { if (active) { setIdeas(data.items); setStatus('ready') } }).catch(() => { if (active) setStatus('error') })
    return () => { active = false }
  }, [])
  return <main className="betaPage productPage"><header className="publicHeading"><div><h1>{text.roadmap}</h1><p>{text.roadmapSubtitle}</p></div></header><p className="publicNote">{text.roadmapNote}</p>
    {Object.entries(productRoadmap).filter(([, keys]) => keys.length).map(([group, keys]) => <section className="publicSection" key={group}><h2>{text[group]}</h2>
      <ul>{keys.map(key => <li key={key} id={key}>{text.roadmapItems[key]}</li>)}</ul></section>)}
    <section className="publicSection"><h2>{text.communityIdeas}</h2>
      {status === 'loading' && <p role="status">{t.beta.loading}</p>}
      {status === 'error' && <p role="alert">{text.roadmapError}</p>}
      {status === 'ready' && !ideas.length && <p>{text.noLinkedIdeas}</p>}
      <ul>{ideas.map(idea => <li key={idea.id}><a href={`/roadmap#${idea.roadmap_key}`}>{idea.title}</a> · {text[idea.development_status]} · {idea.votes} {text.votes}{idea.developer_feedback && <> · {text.developer}</>}</li>)}</ul>
      <a href="/feedback">{text.shareFeedback}</a>
    </section>
  </main>
}
