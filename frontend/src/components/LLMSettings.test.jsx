import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { Simulate } from 'react-dom/test-utils'
import { AppProvider, useApp } from '../context/AppContext'
import { translations } from '../i18n'
import { clearLLMSettings, getLLMSettings } from '../utils/llmSettings'
import LLMSettings from './LLMSettings'

function AssistantState() {
  const { t, llmProvider } = useApp()
  return <><LLMSettings />{!llmProvider && <p>{t.llm.noKey}</p>}<button disabled={!llmProvider}>Send</button></>
}

test('configuration enables the assistant, masks the key, and removal disables it immediately', () => {
  global.IS_REACT_ACT_ENVIRONMENT = true
  clearLLMSettings()
  sessionStorage.clear()
  localStorage.setItem('lang', 'en')
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)
  act(() => root.render(<AppProvider><AssistantState /></AppProvider>))
  expect(container.textContent).toContain(translations.en.llm.noKey)
  expect([...container.querySelectorAll('option')].map(o => o.value)).toEqual(['anthropic', 'gemini'])
  const input = container.querySelector('input[type="password"]')
  input.value = 'test-only-secret'
  act(() => Simulate.submit(container.querySelector('form')))
  expect(getLLMSettings()).toEqual({ provider: 'anthropic', apiKey: 'test-only-secret' })
  expect(input.value).toBe('')
  expect(sessionStorage.length).toBe(0)
  expect(localStorage.getItem('careerflow-llm-session')).toBeNull()
  expect(container.innerHTML).not.toContain('test-only-secret')
  expect(container.textContent).toContain('Claude / Anthropic')
  expect(container.textContent).not.toContain(translations.en.llm.noKey)
  expect([...container.querySelectorAll('button')].find(b => b.textContent === 'Send').disabled).toBe(false)
  // Navigation can remount the panel without losing this page's in-memory key.
  act(() => root.render(<AppProvider><p>Another view</p></AppProvider>))
  act(() => root.render(<AppProvider><AssistantState /></AppProvider>))
  expect(container.querySelector('input[type="password"]').value).toBe('')
  expect(getLLMSettings().apiKey).toBe('test-only-secret')
  expect([...container.querySelectorAll('button')].find(b => b.textContent === 'Send').disabled).toBe(false)
  const remove = [...container.querySelectorAll('button')].find(b => b.textContent === translations.en.llm.remove)
  act(() => remove.click())
  expect(getLLMSettings()).toBeNull()
  expect(container.textContent).toContain(translations.en.llm.noKey)
  expect([...container.querySelectorAll('button')].find(b => b.textContent === 'Send').disabled).toBe(true)
  act(() => root.unmount())
  container.remove()
})
