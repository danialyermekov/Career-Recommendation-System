import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { Simulate } from 'react-dom/test-utils'
import { AppProvider } from '../context/AppContext'
import { submitFeedback } from '../utils/api'
import Feedback from './Feedback'
import { productTranslations } from '../productI18n'
jest.mock('../utils/api')
let container, root
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true
  localStorage.setItem('lang', 'en')
  container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container)
})
afterEach(() => { act(() => root.unmount()); container.remove(); jest.clearAllMocks() })
test.each(['en', 'ru', 'kk'])('feedback validates and submits with confirmation in %s', async lang => {
  localStorage.setItem('lang', lang)
  await act(async () => root.render(<AppProvider><Feedback sessionId="owned-session" /></AppProvider>))
  await act(async () => Simulate.submit(container.querySelector('form')))
  expect(submitFeedback).not.toHaveBeenCalled()
  expect(container.textContent).toContain(productTranslations[lang].submitError)
  expect(container.querySelector('input[type="checkbox"]').checked).toBe(false)
  await act(async () => Simulate.change(container.querySelectorAll('select')[1], { target: { value: '5' } }))
  submitFeedback.mockResolvedValue({ submitted: true })
  await act(async () => Simulate.submit(container.querySelector('form')))
  expect(submitFeedback).toHaveBeenCalledWith({ type: 'review', rating: 5, title: null, message: '', reproduction_steps: '', public_consent: false, session_id: 'owned-session', website: '' })
  expect(container.textContent).toContain(productTranslations[lang].thanks)
  expect(container.textContent).not.toContain(productTranslations[lang].pendingNote)
})
test('failed submissions display a retryable message', async () => {
  await act(async () => root.render(<AppProvider><Feedback /></AppProvider>))
  await act(async () => Simulate.change(container.querySelector('textarea'), { target: { value: 'Suggestion' } }))
  await act(async () => Simulate.change(container.querySelectorAll('select')[1], { target: { value: '3' } }))
  submitFeedback.mockRejectedValue(new Error('private-detail'))
  await act(async () => Simulate.submit(container.querySelector('form')))
  expect(container.textContent).toContain(productTranslations.en.submitError)
  expect(container.textContent).not.toContain('private-detail')
})

test('feature consent is explicit and success never claims immediate publication', async () => {
  await act(async () => root.render(<AppProvider><Feedback /></AppProvider>))
  await act(async () => Simulate.change(container.querySelector('select'), { target: { value: 'feature' } }))
  await act(async () => Simulate.change(container.querySelector('input[maxlength="120"]'), { target: { value: 'New course sources' } }))
  await act(async () => Simulate.change(container.querySelector('textarea'), { target: { value: 'Add more recently updated courses.' } }))
  await act(async () => Simulate.change(container.querySelector('input[type="checkbox"]'), { target: { checked: true } }))
  submitFeedback.mockResolvedValue({ submitted: true })
  await act(async () => Simulate.submit(container.querySelector('form')))
  expect(submitFeedback.mock.calls[0][0]).toMatchObject({ type: 'feature', title: 'New course sources', public_consent: true, rating: null })
  expect(container.textContent).toContain(productTranslations.en.pendingNote)
  expect(container.querySelector('input[type="checkbox"]').checked).toBe(false)
})
