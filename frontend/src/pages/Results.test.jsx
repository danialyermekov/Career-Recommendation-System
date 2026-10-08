import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { Simulate } from 'react-dom/test-utils'
import { TextDecoder, TextEncoder } from 'util'
import { AppProvider } from '../context/AppContext'
import { translations } from '../i18n'
import { clearLLMSettings, getLLMSettings, saveLLMSettings } from '../utils/llmSettings'
import * as api from '../utils/api'
import Results, { getCourseProviderUrl } from './Results'

jest.mock('../utils/api')

describe('getCourseProviderUrl', () => {
  test('returns direct url when course.url is an http link', () => {
    expect(getCourseProviderUrl({ url: 'https://example.com/course', title: 'Python', platform: 'Udemy' }))
      .toBe('https://example.com/course')
  })

  test('returns null when course is missing or falsy', () => {
    expect(getCourseProviderUrl(null)).toBeNull()
    expect(getCourseProviderUrl(undefined)).toBeNull()
  })

  test('constructs search url for Coursera when direct url is missing', () => {
    expect(getCourseProviderUrl({ title: 'Machine Learning Specialization', platform: 'Coursera' }))
      .toBe('https://www.coursera.org/search?query=Machine%20Learning%20Specialization')
  })

  test('constructs search url for Stepik when direct url is missing', () => {
    expect(getCourseProviderUrl({ title: 'Python Generation', platform: 'Stepik' }))
      .toBe('https://stepik.org/catalog/search?q=Python%20Generation')
  })

  test('constructs search url for EdX, Udacity, and Udemy', () => {
    expect(getCourseProviderUrl({ title: 'CS50', platform: 'edX' }))
      .toBe('https://www.edx.org/search?q=CS50')
    expect(getCourseProviderUrl({ title: 'Data Engineer', platform: 'Udacity' }))
      .toBe('https://www.udacity.com/courses/all?search=Data%20Engineer')
    expect(getCourseProviderUrl({ title: 'Complete Web Dev', platform: 'Udemy' }))
      .toBe('https://www.udemy.com/courses/search/?q=Complete%20Web%20Dev')
  })

  test('falls back to Google search when platform is unknown', () => {
    expect(getCourseProviderUrl({ title: 'Intro to Algorithms', platform: 'CustomAcademy' }))
      .toBe('https://www.google.com/search?q=CustomAcademy%20Intro%20to%20Algorithms')
  })
})

describe('Results component', () => {
  const result = {
    session_id: 'test-session', top_profession: 'Data Analyst', alternative_profession: 'Data Scientist',
    final_scores: { 'Data Analyst': 0.8, 'Data Scientist': 0.7 },
    skill_scores: {}, classification_scores: {}, demand_scores: {}, roadmap_with_courses: {},
    full_roadmap: {}, _formData: { skills: ['sql'] },
  }
  let container, root

  beforeEach(async () => {
    global.IS_REACT_ACT_ENVIRONMENT = true
    global.TextDecoder = TextDecoder
    clearLLMSettings()
    sessionStorage.clear()
    localStorage.clear()
    localStorage.setItem('lang', 'en')
    HTMLElement.prototype.scrollIntoView = jest.fn()
    api.getRecommendationHistory.mockResolvedValue({ items: [] })
    api.getRecommendationState.mockResolvedValue({ progress: {} })
    api.saveRoadmapProgress.mockResolvedValue({})
    api.saveCourseFilterPreferences.mockResolvedValue({})
    api.getTrialStatus.mockResolvedValue({ available: false, remaining: 0, total: 3 })
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
    await act(async () => root.render(<AppProvider><Results results={result} /></AppProvider>))
    const open = container.querySelector('.aiFab')
    await act(async () => open.click())
    await act(async () => [...container.querySelectorAll('.advisorModes button')].find(button => button.textContent === translations.en.experience.byok).click())
  })

  afterEach(() => {
    act(() => root.unmount())
    container.remove()
    jest.clearAllMocks()
  })

  test('real assistant is disabled without a key and responds immediately to save/remove', async () => {
    expect(container.textContent).toContain(translations.en.llm.noKey)
    expect(container.querySelector('textarea[placeholder]').disabled).toBe(true)
    await act(async () => saveLLMSettings('anthropic', 'test-only-secret'))
    expect(container.querySelector('textarea[placeholder]').disabled).toBe(false)
    expect(container.querySelector(`button[aria-label="${translations.en.results.voiceRecord}"]`).disabled).toBe(true)
    expect(container.textContent).toContain(translations.en.llm.voiceGemini)
    await act(async () => clearLLMSettings())
    expect(container.querySelector('textarea[placeholder]').disabled).toBe(true)
    expect(container.textContent).toContain(translations.en.llm.noKey)
    expect(api.sendChatStream).not.toHaveBeenCalled()
  })

  test('split SSE chunks preserve text and show safe provider errors without deleting the key', async () => {
    await act(async () => saveLLMSettings('gemini', 'test-only-secret'))
    const stream = 'data: {"type":"text","content":"Career data: advice"}\n\n' +
      'data: {"type":"error","code":"key_rejected","content":"test-only-secret"}\n\n' +
      'data: [DONE]\n\n'
    const chunks = [stream.slice(0, 24), stream.slice(24, 62), stream.slice(62)]
    const reader = { read: jest.fn(async () => chunks.length
      ? { value: new TextEncoder().encode(chunks.shift()), done: false }
      : { done: true }) }
    api.sendChatStream.mockResolvedValue({ ok: true, body: { getReader: () => reader } })
    const input = container.querySelector('textarea[placeholder]')
    await act(async () => Simulate.change(input, { target: { value: 'Career advice', style: {}, scrollHeight: 20 } }))
    await act(async () => container.querySelector(`button[aria-label="${translations.en.results.chatSend}"]`).click())
    expect(container.textContent).toContain(translations.en.llm.errors.key_rejected)
    expect(container.textContent).not.toContain('test-only-secret')
    expect(getLLMSettings().apiKey).toBe('test-only-secret')
    const history = api.sendChatStream.mock.calls[0][0].history
    expect(history.some(m => m.content === 'Career advice')).toBe(false)
  })

  test('AI CTA button is rendered near top recommendation and dynamically updates label', async () => {
    const ctaBtn = container.querySelector('button[aria-label*="Ask"]')
    expect(ctaBtn).not.toBeNull()
    expect(ctaBtn.textContent).toContain(translations.en.results.askAiRecommendation)

    await act(async () => saveLLMSettings('anthropic', 'test-key'))
    expect(ctaBtn.textContent).toContain(translations.en.results.askClaudeRecommendation)

    await act(async () => saveLLMSettings('gemini', 'test-key'))
    expect(ctaBtn.textContent).toContain(translations.en.results.askGeminiRecommendation)
  })

  test('clicking AI CTA button opens the AI Advisor drawer', async () => {
    // Close the drawer first
    const closeBtn = container.querySelector(`button[title="${translations.en.results.closeAiPanel}"]`)
    expect(closeBtn).not.toBeNull()
    await act(async () => closeBtn.click())
    expect(container.querySelector('.chatSidebar')).toBeNull()

    // Click the top recommendation CTA button
    const ctaBtn = container.querySelector('button[aria-label*="Ask"]')
    expect(ctaBtn).not.toBeNull()
    await act(async () => ctaBtn.click())

    // Drawer is open again
    expect(container.querySelector('.chatSidebar')).not.toBeNull()
  })

  test('failed state loading never overwrites saved progress with empty defaults', async () => {
    act(() => root.unmount())
    root = createRoot(container)
    api.getRecommendationState.mockRejectedValue(new Error('Storage unavailable'))
    api.saveRoadmapProgress.mockClear()
    api.saveCourseFilterPreferences.mockClear()
    await act(async () => root.render(<AppProvider><Results results={result} /></AppProvider>))
    await act(async () => new Promise(resolve => setTimeout(resolve, 450)))
    expect(api.saveRoadmapProgress).not.toHaveBeenCalled()
    expect(api.saveCourseFilterPreferences).not.toHaveBeenCalled()
    expect(container.textContent).toContain(translations.en.beta.saveError)
  })
})
