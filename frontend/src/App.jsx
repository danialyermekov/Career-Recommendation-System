import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { AppProvider, useApp } from './context/AppContext'
import Navbar from './components/Navbar'
import Hero from './pages/Hero'
import Form from './pages/Form'
import Results from './pages/Results'
import { getRecommendation, getRecommendationState } from './utils/api'
import { rememberDemoSession, isDemoSession } from './utils/demoProfile'
import './index.css'

function AppInner() {
  const { t } = useApp()
  const [page, setPage] = useState('hero')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState('')
  const [demo, setDemo] = useState(false)

  useEffect(() => {
    let cancelled = false
    const route = async () => {
      const hash = window.location.hash
      if (hash === '#profile') { setPage('form'); return }
      const sessionId = hash.match(/^#results\/([a-zA-Z0-9-]+)$/)?.[1]
      if (!sessionId) { setPage('hero'); return }
      if (results?.session_id === sessionId) { setPage('results'); return }
      setLoading(true)
      try {
        const state = await getRecommendationState(sessionId)
        if (!cancelled && window.location.hash === hash) {
          setResults({ ...state.results, _isDemo: isDemoSession(sessionId) })
          setPage('results')
        }
      } catch {
        if (!cancelled && window.location.hash === hash) { setError(t.errors.api); setPage('form') }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    route()
    window.addEventListener('hashchange', route)
    return () => { cancelled = true; window.removeEventListener('hashchange', route) }
  }, [results, t.errors.api])

  useEffect(() => { window.scrollTo(0, 0) }, [page])

  const handleStart = () => { setDemo(false); setError(''); window.location.hash = 'profile'; setPage('form') }
  const handleDemo = () => { setDemo(true); setError(''); window.location.hash = 'profile'; setPage('form') }
  const handleBack = () => { window.location.hash = ''; setPage('hero') }
  const showResult = data => {
    setResults(data)
    window.location.hash = `results/${data.session_id}`
    setPage('results')
  }

  const handleSubmit = async (profile, isDemo = false) => {
    setLoading(true)
    setError('')
    try {
      const data = await getRecommendation(profile)
      if (isDemo) rememberDemoSession(data.session_id)
      showResult({ ...data, _formData: profile, _isDemo: isDemo })
    } catch (e) {
      setError(t.errors.api)
    } finally {
      setLoading(false)
    }
  }

  const pageVariants = {
    initial: { opacity: 0, scale: 0.975, y: 18, filter: 'blur(10px)' },
    animate: { opacity: 1, scale: 1, y: 0, filter: 'blur(0px)' },
    exit: { opacity: 0, scale: 1.025, y: -18, filter: 'blur(10px)' },
  }

  return (
    <div className="appShell">
      <div className="dataGrid" aria-hidden="true" />

      <Navbar onLogoClick={handleBack} />

      <AnimatePresence mode="wait">
        {page === 'hero' && (
          <motion.main
            key="hero"
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
          >
            <Hero onStart={handleStart} onDemo={handleDemo} />
          </motion.main>
        )}

        {page === 'form' && (
          <motion.main
            key="form"
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
          >
            {error && (
              <div className="appError">
                {error}
              </div>
            )}
            <Form onSubmit={handleSubmit} loading={loading} initialDemo={demo} />
          </motion.main>
        )}

        {page === 'results' && results && (
          <motion.main
            key="results"
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
          >
            <Results results={results} onBack={handleBack} onRetry={handleStart} onHistorySelect={showResult} />
          </motion.main>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function App() {
  return (
    <AppProvider>
      <AppInner />
    </AppProvider>
  )
}
