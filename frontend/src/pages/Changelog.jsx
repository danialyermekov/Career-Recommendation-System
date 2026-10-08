import { useApp } from '../context/AppContext'
import { productUpdates } from '../data/productUpdates'

export default function Changelog() {
  const { t, lang } = useApp()
  const text = t.product
  return <main className="betaPage productPage"><header className="publicHeading"><div><h1>{text.changelog}</h1><p>{text.changelogSubtitle}</p></div></header>
    <p className="publicNote">{text.releaseNote}</p>
    <ol className="releaseTimeline">{productUpdates.map(update => <li key={update.commit}>
      <time dateTime={update.date}>{new Date(`${update.date}T12:00:00Z`).toLocaleDateString(lang === 'kk' ? 'kk-KZ' : lang, { year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC' })}</time>
      <h2>{text[update.title]}</h2><ul>{text[update.changes].map(change => <li key={change}>{change}</li>)}</ul>
      <a href={`https://github.com/danialyermekov/Career-Recommendation-System/commit/${update.commit}`} target="_blank" rel="noopener noreferrer">{text.sourceCommit} · {update.commit.slice(0, 7)}</a>
    </li>)}</ol>
  </main>
}
