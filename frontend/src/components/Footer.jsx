import { useRef } from 'react'
import { useApp } from '../context/AppContext'
import styles from '../pages/Hero.module.css'
import BrandLogo from './BrandLogo'

export default function Footer() {
  const { t } = useApp()
  const dialog = useRef(null)
  return <div className="siteFooter">
    <footer className={styles.footer}>
      <div className={styles.footerBrand}><a href="/" aria-label="CareerFlow"><BrandLogo /></a><span>© 2026 CareerFlow · {t.beta.beta}</span><p>{t.footer.maintainer}</p></div>
      <nav aria-label={t.footer.links}>
        <a href="https://careerflow.live">careerflow.live</a>
        <a href="/">{t.product.home}</a><a href="/about">{t.product.about}</a><a href="/contact">{t.beta.contact}</a>
        <button type="button" onClick={() => dialog.current.showModal()}>{t.footer.privacy}</button>
        <a href="/terms">{t.beta.terms}</a><a href="/disclaimer">{t.beta.disclaimer}</a>
        <a href="/privacy">{t.beta.fullPrivacy}</a>
        <a href="https://github.com/danialyermekov/Career-Recommendation-System" target="_blank" rel="noopener noreferrer">GitHub</a>
        <a href="mailto:contact@careerflow.live">{t.footer.contact}: contact@careerflow.live</a>
        <a href="https://www.linkedin.com/in/danial-yermekov/" target="_blank" rel="noopener noreferrer">LinkedIn</a>
        <a href="/feedback">{t.product.feedback}</a><a href="/changelog">{t.product.changelog}</a><a href="/roadmap">{t.product.roadmap}</a>
      </nav>
    </footer>
    <dialog ref={dialog} className={styles.privacyDialog} aria-labelledby="privacy-title">
      <div className={styles.privacyHeader}><h2 id="privacy-title">{t.footer.privacy}</h2>
        <form method="dialog"><button type="submit">{t.footer.close}</button></form></div>
      {t.beta.privacyText.map((text, index) => <p key={text}>{(index === 2 ? t.product.feedbackPrivacy : text).split('contact@careerflow.live').map((part, i) => <span key={i}>{i > 0 && <a href="mailto:contact@careerflow.live">contact@careerflow.live</a>}{part}</span>)}</p>)}
      <p>{t.experience.privacy}</p>
      <a href="/privacy" onClick={() => dialog.current.close()}>{t.beta.fullPrivacy}</a>
    </dialog>
  </div>
}
