import { useApp } from '../context/AppContext'
import styles from './Navbar.module.css'

const SunIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="5"/>
    <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
  </svg>
)

const MoonIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
  </svg>
)

const LogoMark = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M3 15C7 15 5 9 9 9S11 15 15 15S17 9 21 9" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

export default function Navbar({ onLogoClick }) {
  const { theme, toggleTheme, lang, setLanguage, t } = useApp()
  const languages = [
    { key: 'en', label: 'EN' },
    { key: 'ru', label: 'RU' },
    { key: 'kk', label: 'KZ' },
  ]

  return (
    <nav className={styles.nav}>
      <div className={styles.inner}>
        <button className={styles.logo} onClick={onLogoClick} aria-label={t.nav.title}>
          <span className={styles.logoMark}><LogoMark /></span>
          <span className={styles.logoText}>{t.nav.title}</span>
        </button>
        <div className={styles.actions}>
          <button className={styles.iconBtn} onClick={toggleTheme} title={t.nav.themeToggle || t.nav.theme}>
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </button>
          <div className={styles.langGroup} aria-label={t.nav.language || 'Language'}>
            {languages.map(item => (
              <button
                key={item.key}
                className={`${styles.langBtn} ${lang === item.key ? styles.langBtnActive : ''}`}
                onClick={() => setLanguage(item.key)}
                aria-pressed={lang === item.key}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </nav>
  )
}
