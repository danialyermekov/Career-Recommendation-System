import { useApp } from '../context/AppContext'

const technologies = ['Python', 'FastAPI', 'React', 'PostgreSQL', 'Supabase Auth', 'CatBoost', 'LightGBM', 'scikit-learn', 'Docker']
export default function About({ onExploreAdvisor }) {
  const { t } = useApp()
  const text = t.product
  return <main className="betaPage productPage"><h1>{text.about}</h1>
    <section className="publicSection"><h2>{text.whatTitle}</h2><p>{text.whatText}</p><p>{text.betaNote}</p></section>
    <section className="publicSection"><h2>{text.howTitle}</h2><ol>{text.howSteps.map(step => <li key={step}>{step}</li>)}</ol><p className="publicNote">{text.limitation}</p></section>
    <section className="publicSection"><h2>{text.technology}</h2><ul className="technologyList">{technologies.map(name => <li key={name}>{name}</li>)}</ul></section>
    <section className="publicSection"><h2>{text.developerTitle}</h2><h3>Danial Yermekov</h3><p>{text.developerRole}</p><p>{text.developerText}</p>
      <p className="publicLinks"><a href="https://github.com/danialyermekov" target="_blank" rel="noopener noreferrer">GitHub</a><a href="https://www.linkedin.com/in/danial-yermekov/" target="_blank" rel="noopener noreferrer">LinkedIn</a></p>
      <p><a href="https://github.com/danialyermekov/Career-Recommendation-System#contributors" target="_blank" rel="noopener noreferrer">{text.historicalCredits}</a></p>
      <p>{t.experience.contact} <a href="mailto:contact@careerflow.live">contact@careerflow.live</a></p>
    </section>
    <aside className="advisorShowcase" aria-labelledby="advisor-showcase-title"><h2 id="advisor-showcase-title">{text.aiTitle}</h2><p>{text.aiText}</p>
      <ul>{text.aiCapabilities.map(item => <li key={item}>{item}</li>)}</ul><p className="publicNote">{t.experience.byokText}</p><p>{text.aiProvider}</p>
      <button type="button" onClick={onExploreAdvisor}>{text.aiExplore}</button><p>{text.aiNext}</p>
    </aside>
    <p className="publicLinks"><a href="/feedback">{text.feedback}</a><a href="/changelog">{text.changelog}</a><a href="/roadmap">{text.roadmap}</a></p>
  </main>
}
