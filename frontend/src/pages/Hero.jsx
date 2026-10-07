import { useRef } from 'react'
import { useApp } from '../context/AppContext'
import styles from './Hero.module.css'

const features = [
  { icon: '01', key: 0 },
  { icon: '02', key: 1 },
  { icon: '03', key: 2 },
]

export default function Hero({ onStart, onDemo }) {
  const { t, lang } = useApp()
  const privacyDialog = useRef(null)
  const metrics = [
    { value: '7', label: t.hero.metrics?.[0] || 'career tracks' },
    { value: t.hero.noAiKey, label: t.hero.metrics[1], text: true },
    { value: '4', label: t.hero.metrics?.[2] || 'signals' },
  ]

  return (
    <>
    <div className={styles.hero}>
      <div className={styles.grid} aria-hidden="true" />
      <div className={styles.orbit} aria-hidden="true">
        <span className={styles.nodeA} />
        <span className={styles.nodeB} />
        <span className={styles.nodeC} />
      </div>

      <section className={styles.content}>
        <div className={styles.kicker}>
          <span className={styles.kickerLine} />
          <span>{t.hero.badge}</span>
        </div>

        <h1 className={`${styles.title} ${lang !== 'en' ? styles.titleCyrillic : ''}`}>
          <span>{t.hero.title}</span>
        </h1>

        <p className={styles.subtitle}>{t.hero.subtitle}</p>

        <div className={styles.metrics} aria-label="Project capabilities">
          {metrics.map(item => (
            <div key={item.label}>
              <strong className={item.text ? styles.metricText : undefined}>{item.value}</strong>
              <span>{item.label}</span>
            </div>
          ))}
        </div>

        <div className={styles.features}>
          {features.map((f, i) => (
            <div key={f.key} className={styles.feature} style={{ animationDelay: `${0.1 + i * 0.08}s` }}>
              <span className={styles.featureIcon}>{f.icon}</span>
              <span>{t.hero.features[i]}</span>
            </div>
          ))}
        </div>

        <div className={styles.ctaGroup}>
        <button className={styles.cta} onClick={onStart}>
          {t.hero.cta}
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="5" y1="12" x2="19" y2="12"/>
            <polyline points="12 5 19 12 12 19"/>
          </svg>
        </button>
        <button className={styles.secondaryCta} onClick={onDemo}>{t.review.demo}</button>
        </div>

        <a className={styles.scrollCue} href="#how-it-works">
          <span />
          <small>{t.hero.footer || 'profile · skills · market'}</small>
        </a>
      </section>

      <aside className={styles.methodPanel} aria-label={t.hero.panelTitle}>
        <div className={styles.panelHeader}>
          <span className={styles.panelIndex}>04</span>
          <span>{t.hero.panelTitle}</span>
        </div>
        <div className={styles.panelSteps}>
          {(t.hero.panelItems || []).map((item, index) => (
            <div key={item.label} className={styles.panelStep}>
              <div className={styles.panelStepNum}>{String(index + 1).padStart(2, '0')}</div>
              <div className={styles.panelStepBody}>
                <strong>{item.label}</strong>
                <span>{item.text}</span>
              </div>
            </div>
          ))}
        </div>
        <div className={styles.panelFooter}>
          <span />
          <small>{t.hero.features?.join(' · ')}</small>
        </div>
      </aside>
    </div>
    <div className={styles.explainer}>
      <section className={styles.explainerSection} id="how-it-works">
        <h2>{t.review.howTitle}</h2>
        <p className={styles.sectionIntro}>{t.review.howIntro}</p>
        <ol className={styles.flow}>
          {t.review.steps.map(([title, text], index) => (
            <li key={title}>
              <span className={styles.stepNumber}>{String(index + 1).padStart(2, '0')}</span>
              <h3>{title}</h3><p>{text}</p>
            </li>
          ))}
        </ol>
      </section>
      <section className={styles.explainerSection}>
        <h2>{t.review.inspectTitle}</h2>
        <p className={styles.sectionIntro}>{t.review.inspectIntro}</p>
        <div className={styles.signalGrid}>
          {t.review.signals.map(([title, text], index) => (
            <article className={styles.infoCard} key={title}>
              <span className={styles.stepNumber}>0{index + 1}</span><h3>{title}</h3><p>{text}</p>
            </article>
          ))}
        </div>
        <p className={styles.contextNote}>{t.review.inspectNote}</p>
      </section>
      <section className={styles.explainerSection}>
        <h2>{t.review.dataTitle}</h2>
        <div className={styles.dataGrid}>
          <article className={styles.infoCard}>
            <h3>{t.review.jobsTitle}</h3><p>{t.review.jobsText}</p>
            <a className={styles.sourceLink} href="https://huggingface.co/datasets/lukebarousse/data_jobs" target="_blank" rel="noopener noreferrer">Data Jobs · Hugging Face ↗</a>
          </article>
          <article className={styles.infoCard}>
            <h3>{t.review.profileTitle}</h3><p>{t.review.profileText}</p>
            <a className={styles.sourceLink} href="https://www.kaggle.com/datasets/hafsaatm/career-path-recommendation" target="_blank" rel="noopener noreferrer">Career Path Recommendation · Kaggle ↗</a>
          </article>
        </div>
        <details className={styles.sourceDetails}>
          <summary>{t.review.sources}</summary><p>{t.review.sourceNote}</p>
          <p><code>vacancy_data.csv</code> · <code>career_multilabel_dataset.csv</code></p>
        </details>
        <p className={styles.contextNote}>{t.review.tracksNote}</p>
      </section>
      <section className={styles.explainerSection}>
        <h2>{t.review.roadmapTitle}</h2>
        <p className={styles.sectionIntro}>{t.review.roadmapText}</p>
        <ol className={styles.roadmapFlow}>
          {t.review.roadmapSteps.map(text => <li key={text}>{text}</li>)}
        </ol>
        <p className={styles.contextNote}>{t.review.roadmapNote}</p>
      </section>
      <section className={`${styles.explainerSection} ${styles.finalCta}`}>
        <h2>{t.review.ctaTitle}</h2><p>{t.review.ctaText}</p>
        <div className={styles.ctaGroup}>
          <button className={styles.cta} onClick={onDemo}>{t.review.demo}</button>
          <button className={styles.secondaryCta} onClick={onStart}>{t.review.start}</button>
        </div>
        <p className={styles.contextNote}>{t.review.aiNote}</p>
      </section>
      <footer className={styles.footer}>
        <span>© 2026 CareerFlow</span>
        <nav aria-label={t.footer.links}>
          <a href="https://careerflow.live">careerflow.live</a>
          <button type="button" onClick={() => privacyDialog.current.showModal()}>{t.footer.privacy}</button>
        </nav>
      </footer>
      <dialog ref={privacyDialog} className={styles.privacyDialog} aria-labelledby="privacy-title">
        <div className={styles.privacyHeader}>
          <h2 id="privacy-title">{t.footer.privacy}</h2>
          <form method="dialog"><button type="submit">{t.footer.close}</button></form>
        </div>
        {t.footer.paragraphs.map(text => <p key={text}>{text}</p>)}
      </dialog>
    </div>
    </>
  )
}
