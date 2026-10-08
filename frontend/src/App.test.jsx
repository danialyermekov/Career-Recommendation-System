import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { Simulate } from 'react-dom/test-utils'
import App from './App'
import { DEMO_PROFILE, isDemoSession } from './utils/demoProfile'
import * as api from './utils/api'

jest.mock('./utils/api')
jest.mock('framer-motion', () => {
  const React = require('react')
  const passthrough = ({ children }) => React.createElement('main', null, children)
  return { AnimatePresence: passthrough, motion: { main: passthrough } }
})

const result = {
  session_id: 'review-test-session', top_profession: 'Data Analyst', alternative_profession: 'Data Scientist',
  final_scores: { 'Data Analyst': 0.905, 'Data Scientist': 0.3933 },
  classification_scores: { 'Data Analyst': 0.6, 'Data Scientist': 0.2 },
  skill_scores: { 'Data Analyst': 0.3, 'Data Scientist': 0.15 },
  demand_scores: { 'Data Analyst': { trend_score: 0.8, market_share: 0.6, predicted_vacancies: 500 }, 'Data Scientist': { trend_score: 0.4, market_share: 0.2, predicted_vacancies: 200 } },
  scoring_weights: { classifier: 0.38, skill_matcher: 0.35, demand_trend: 0.2, demand_market_share: 0.07 },
  roadmap_with_courses: { analyst_tools: { tableau: { courses: [] } } },
  full_roadmap: { analyst_tools: ['tableau', 'excel'] },
  _formData: DEMO_PROFILE,
}
let container, root
const button = text => [...container.querySelectorAll('button')].find(el => el.textContent === text)
const tourButton = text => [...container.querySelectorAll('.guidedTour button')].find(el => el.textContent === text)

beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true
  window.history.replaceState({}, '', '/')
  localStorage.clear(); sessionStorage.clear(); localStorage.setItem('lang', 'en')
  window.scrollTo = jest.fn()
  HTMLElement.prototype.scrollIntoView = jest.fn()
  api.getRecommendation.mockResolvedValue(result)
  api.getRecommendationHistory.mockResolvedValue({ items: [] })
  api.getRecommendationState.mockResolvedValue({ results: result, progress: {} })
  api.saveRoadmapProgress.mockResolvedValue({})
  api.saveCourseFilterPreferences.mockResolvedValue({})
  api.filterCourses.mockResolvedValue({})
  api.getPublicFeedback.mockResolvedValue({ items: [], has_more: false })
  api.getPublicRoadmap.mockResolvedValue({ items: [], has_more: false })
  api.getTrialStatus.mockResolvedValue({ available: false, remaining: 0, total: 3 })
  container = document.createElement('div'); document.body.appendChild(container)
  root = createRoot(container)
})
afterEach(() => { act(() => root.unmount()); container.remove(); jest.clearAllMocks() })

test('original horizontal branding appears in navbar and footer in both themes and keeps home navigation', async () => {
  window.history.replaceState({}, '', '/#about')
  await act(async () => root.render(<App />))
  const home = container.querySelector('nav a[aria-label="CareerFlow"]')
  const headerLogo = home.querySelector('img[alt="CareerFlow"]')
  const footerLogo = container.querySelector('footer img[alt="CareerFlow"]')
  expect(headerLogo.getAttribute('src')).toBe('/branding/careerflow-horizontal.png')
  expect(headerLogo.getAttribute('width')).toBe('624')
  expect(headerLogo.getAttribute('height')).toBe('72')
  expect(home.querySelector('source').getAttribute('srcset')).toBe('/branding/careerflow-horizontal.webp')
  expect(footerLogo.getAttribute('src')).toBe(headerLogo.getAttribute('src'))
  expect(home.querySelector('svg')).toBeNull()
  expect(document.documentElement.dataset.theme).toBe('dark')
  await act(async () => container.querySelector('nav button[title]').click())
  expect(document.documentElement.dataset.theme).toBe('light')
  expect(home.querySelector('img')).toBe(headerLogo)
  await act(async () => home.click())
  expect(window.location.hash).toBe('')
  expect(container.textContent).toContain('How CareerFlow works')
})

test('live demo calls the real API directly and guides all five steps without an AI request', async () => {
  await act(async () => root.render(<App />))
  expect(container.textContent).toContain('How CareerFlow works')
  expect(container.textContent).toContain('No AI key required')
  expect(container.textContent).toContain('limited free AI preview')
  expect(container.textContent).not.toContain('generates examples for missing classes')
  expect([...container.querySelectorAll('a')].map(a => a.href)).toEqual(expect.arrayContaining([
    'https://huggingface.co/datasets/lukebarousse/data_jobs',
    'https://www.kaggle.com/datasets/hafsaatm/career-path-recommendation',
  ]))
  await act(async () => button('Try Live Demo').click())
  expect(api.getRecommendation).toHaveBeenCalledWith({ ...DEMO_PROFILE, lang: 'en' }, { demo: true })
  expect(container.querySelector('#profile-gpa')).toBeNull()
  expect(isDemoSession(result.session_id)).toBe(true)
  expect(window.location.hash).toBe('#results/review-test-session')
  expect(container.textContent).toContain('90.5 / 100')
  expect(container.textContent).toContain('28.50 points')
  expect(container.textContent).toContain('0.60000')
  expect(container.querySelectorAll('.aiFab')).toHaveLength(1)
  expect(container.querySelector('.guidedTour').textContent).toContain('Your Recommendation')
  await act(async () => button('Next').click())
  expect(container.querySelector('.guidedTour').textContent).toContain('Why This Career?')
  await act(async () => tourButton('Back').click())
  expect(container.querySelector('.guidedTour').textContent).toContain('Your Recommendation')
  await act(async () => button('Next').click())
  await act(async () => button('Next').click())
  expect(container.querySelector('.guidedTour').textContent).toContain('Compare Career Paths')
  await act(async () => button('Next').click())
  expect(container.textContent).toContain('Tableau')
  expect(container.textContent).toContain('Completed 0 of 1 steps')
  await act(async () => container.querySelector('button[aria-label="Tableau"][aria-pressed]').click())
  expect(container.textContent).toContain('Completed 1 of 1 steps')
  await act(async () => button('Next').click())
  expect(container.querySelector('.guidedTour').textContent).toContain('Continue Your Journey')
  expect(container.querySelector('.guidedTour a').getAttribute('href')).toBe('/#login')
  await act(async () => button('Skip Tour').click())
  expect(container.querySelector('.guidedTour')).toBeNull()
  await act(async () => button('History').click())
  expect(container.textContent).toContain('Your account history is private')
  expect(api.sendChatStream).not.toHaveBeenCalled()
  expect(api.sendTrialMessage).not.toHaveBeenCalled()
  expect(api.getRecommendationHistory).not.toHaveBeenCalled()
})

test('normal empty and partial profiles keep GPA validation and accept optional defaults', async () => {
  window.history.replaceState({}, '', '/#profile')
  await act(async () => root.render(<App />))
  expect(container.textContent).not.toContain('25%')
  await act(async () => Simulate.submit(container.querySelector('form')))
  expect(api.getRecommendation).not.toHaveBeenCalled()
  await act(async () => Simulate.change(container.querySelector('#profile-gpa'), { target: { value: '3.1' } }))
  await act(async () => Simulate.submit(container.querySelector('form')))
  expect(api.getRecommendation.mock.calls[0][0]).toMatchObject({ gpa: 3.1, skills: [], python: 0, communication: 3 })
  expect(container.querySelector('.demoBadge')).toBeNull()
})

test('keyboard Escape skips the demo without calling an AI provider', async () => {
  await act(async () => root.render(<App />))
  await act(async () => button('Try Live Demo').click())
  expect(document.activeElement).toBe(container.querySelector('.guidedTour'))
  await act(async () => Simulate.keyDown(container.querySelector('.guidedTour'), { key: 'Escape' }))
  expect(container.querySelector('.guidedTour')).toBeNull()
  expect(api.sendTrialMessage).not.toHaveBeenCalled()
})

test.each(['contact', 'about', 'privacy', 'terms', 'feedback'])('%s uses clickable public contact without personal addresses', async page => {
  window.history.replaceState({}, '', `/${page}`)
  await act(async () => root.render(<App />))
  expect(container.querySelector('main a[href="mailto:contact@careerflow.live"]')).not.toBeNull()
  expect(container.textContent).not.toContain('founder@careerflow.live')
  expect(container.querySelector('footer a[href="mailto:contact@careerflow.live"]')).not.toBeNull()
})

test('a direct result URL reloads the saved result through the existing state endpoint', async () => {
  window.history.replaceState({}, '', '/#results/review-test-session')
  await act(async () => root.render(<App />))
  expect(api.getRecommendationState).toHaveBeenCalledWith('review-test-session')
  expect(container.textContent).toContain('Your recommendation')
  expect(container.textContent).toContain('90.5 / 100')
  expect(api.getRecommendation).not.toHaveBeenCalled()
})


test('PDF uses the selected career, score units and historical market context', async () => {
  window.history.replaceState({}, '', '/#results/review-test-session')
  await act(async () => root.render(<App />))
  const alternative = [...container.querySelectorAll('.professionBarRow')].find(el => el.textContent.includes('Data Scientist'))
  await act(async () => alternative.click())
  const write = jest.fn()
  const open = jest.spyOn(window, 'open').mockReturnValue({ document: { write, close: jest.fn() } })
  try {
    await act(async () => button('Download PDF').click())
    const html = write.mock.calls[0][0]
    expect(html).toContain('<title>Learning roadmap: Data Scientist</title>')
    expect(html).toContain('39.3 / 100')
    expect(html).toContain('2023')
    expect(html).toContain('not a probability')
  } finally { open.mockRestore() }
})


test.each([
  ['en', 'Contact', 'Developed and maintained by Danial Yermekov.', 'Privacy'],
  ['ru', 'Контакт', 'Разработку и поддержку осуществляет Danial Yermekov.', 'Конфиденциальность'],
  ['kk', 'Байланыс', 'Әзірлеу мен қолдауды Danial Yermekov жүзеге асырады.', 'Құпиялық'],
])('footer shows project contacts and maintainer and opens privacy in %s', async (lang, contact, maintainer, privacy) => {
  localStorage.setItem('lang', lang)
  const showModal = jest.fn()
  await act(async () => root.render(<App />))
  const footer = container.querySelector('footer')
  expect(footer.textContent).toContain('© 2026 CareerFlow')
  expect(footer.textContent).toContain(maintainer)
  for (const [label, href] of [
    ['GitHub', 'https://github.com/danialyermekov/Career-Recommendation-System'],
    ['LinkedIn', 'https://www.linkedin.com/in/danial-yermekov/'],
  ]) {
    const link = footer.querySelector(`a[href="${href}"]`)
    expect(link).not.toBeNull()
    expect(link.textContent).toBe(label)
    expect(link.target).toBe('_blank')
    expect(link.rel).toBe('noopener noreferrer')
  }
  expect(footer.querySelector('a[href="https://careerflow.live"]')).not.toBeNull()
  const email = footer.querySelector('a[href="mailto:contact@careerflow.live"]')
  expect(email).not.toBeNull()
  expect(email.textContent).toBe(`${contact}: contact@careerflow.live`)
  const dialog = container.querySelector('dialog')
  dialog.showModal = showModal
  await act(async () => button(privacy).click())
  expect(showModal).toHaveBeenCalledTimes(1)
  expect(dialog.getAttribute('aria-labelledby')).toBe('privacy-title')
  if (lang === 'en') {
    expect(dialog.textContent).toContain('Every private API request verifies your Supabase session and checks ownership')
    expect(dialog.textContent).toContain('until refresh')
    expect(dialog.textContent).toContain('only for the AI request')
  }
  expect(dialog.textContent).toContain('PostgreSQL')
  expect(dialog.querySelector('form').getAttribute('method')).toBe('dialog')
})

test.each(['about', 'contact', 'privacy', 'terms', 'disclaimer', 'feedback', 'changelog', 'roadmap', 'login'])('public %s route stays available without signing in', async page => {
  window.history.replaceState({}, '', `/#${page}`)
  localStorage.setItem('career-recommendation-history', 'old-private-data')
  await act(async () => root.render(<App />))
  expect(container.querySelector('.betaPage')).not.toBeNull()
  expect(container.textContent).not.toContain('old-private-data')
  expect(api.getRecommendationHistory).not.toHaveBeenCalled()
  expect(container.querySelector('footer')).not.toBeNull()
  expect(container.querySelector('a[href="/about"]')).not.toBeNull()
})

test.each(['about', 'feedback', 'changelog', 'roadmap'])('clean /%s route works on direct load and popstate', async page => {
  window.history.replaceState({}, '', `/${page}`)
  await act(async () => root.render(<App />))
  expect(container.querySelector('h1').textContent).toBe(require('./productI18n').productTranslations.en[page])
  expect(document.title).toBe(require('./data/seo.json').pages[`/${page}`].title)
  window.history.pushState({}, '', '/about')
  await act(async () => window.dispatchEvent(new PopStateEvent('popstate')))
  expect(container.textContent).toContain('Developer & Maintainer')
  expect(container.textContent).not.toContain('Nurbek Seiilbek')
  expect(container.textContent).not.toContain('Turan Tastan')
})

test('About AI CTA enters the real recommendation and advisor flow without sending an AI request', async () => {
  window.history.replaceState({}, '', '/about')
  await act(async () => root.render(<App />))
  expect(container.textContent).toContain('limited free AI preview')
  await act(async () => button('Explore AI Advisor').click())
  expect(window.location.pathname).toBe('/')
  expect(window.location.hash).toBe('#profile')
  await act(async () => Simulate.change(container.querySelector('#profile-gpa'), { target: { value: '3.1' } }))
  await act(async () => Simulate.submit(container.querySelector('form')))
  expect(container.querySelector('.chatSidebar')).not.toBeNull()
  expect(api.sendChatStream).not.toHaveBeenCalled()
})
