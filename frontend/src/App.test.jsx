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
  container = document.createElement('div'); document.body.appendChild(container)
  root = createRoot(container)
})
afterEach(() => { act(() => root.unmount()); container.remove(); jest.clearAllMocks() })

test('demo follows the normal form/API path, explains the score and reaches roadmap/history without an AI key', async () => {
  await act(async () => root.render(<App />))
  expect(container.textContent).toContain('How CareerFlow works')
  expect(container.textContent).toContain('No AI key required')
  expect(container.textContent).toContain('refresh the page to clear it')
  expect(container.textContent).not.toContain('generates examples for missing classes')
  expect([...container.querySelectorAll('a')].map(a => a.href)).toEqual(expect.arrayContaining([
    'https://huggingface.co/datasets/lukebarousse/data_jobs',
    'https://www.kaggle.com/datasets/hafsaatm/career-path-recommendation',
  ]))
  await act(async () => button('Use demo profile').click())
  expect(container.querySelector('#profile-gpa').value).toBe('3.2')
  expect(container.textContent).toContain('Demo profile')
  await act(async () => Simulate.submit(container.querySelector('form')))
  expect(api.getRecommendation).toHaveBeenCalledWith({ ...DEMO_PROFILE, gpa: 3.2, lang: 'en' })
  expect(isDemoSession(result.session_id)).toBe(true)
  expect(window.location.hash).toBe('#results/review-test-session')
  expect(container.textContent).toContain('90.5 / 100')
  expect(container.textContent).toContain('28.50 points')
  expect(container.textContent).toContain('0.60000')
  expect(container.querySelectorAll('.aiFab')).toHaveLength(1)
  await act(async () => button('Learning roadmap').click())
  expect(container.textContent).toContain('Tableau')
  expect(container.textContent).toContain('Completed 0 of 1 steps')
  await act(async () => button('History').click())
  expect(container.textContent).toContain('Shared demonstration history')
  expect(api.sendChatStream).not.toHaveBeenCalled()
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


test('footer links use careerflow.live, exclude GitHub and open the accurate MVP privacy notice', async () => {
  const showModal = jest.fn()
  await act(async () => root.render(<App />))
  const footer = container.querySelector('footer')
  expect(footer.textContent).toContain('© 2026 CareerFlow')
  expect(footer.querySelector('a[href*="github.com"]')).toBeNull()
  expect(footer.querySelector('a[href="https://careerflow.live"]')).not.toBeNull()
  expect(footer.querySelector('a[href^="mailto:"]')).toBeNull()
  const dialog = container.querySelector('dialog')
  dialog.showModal = showModal
  await act(async () => button('Privacy').click())
  expect(showModal).toHaveBeenCalledTimes(1)
  expect(dialog.getAttribute('aria-labelledby')).toBe('privacy-title')
  expect(dialog.textContent).toContain('shared demo account without sign-in or private access controls')
  expect(dialog.textContent).toContain('SQLite')
  expect(dialog.textContent).toContain('cleared by a full refresh')
  expect(dialog.textContent).toContain('only with the AI request that needs it')
  expect(dialog.querySelector('form').getAttribute('method')).toBe('dialog')
})
