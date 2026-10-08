import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { AppProvider } from '../context/AppContext'
import { useAuth } from '../context/AuthContext'
import { getPublicFeedback, voteFeedback } from '../utils/api'
import FeedbackPage from './FeedbackPage'
jest.mock('../utils/api')
jest.mock('../context/AuthContext', () => ({ useAuth: jest.fn() }))
let container, root
const feature = { id: 'feature-id', type: 'feature', title: '<script>unsafe()</script>', message: 'A real suggestion', votes: 0, voted: false,
  development_status: 'suggested', created_at: '2026-10-09T12:00:00Z', developer_feedback: false }
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true
  localStorage.clear(); sessionStorage.clear(); localStorage.setItem('lang', 'en')
  useAuth.mockReturnValue({ user: null })
  getPublicFeedback.mockResolvedValue({ items: [], has_more: false })
  container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container)
})
afterEach(() => { act(() => root.unmount()); container.remove(); jest.clearAllMocks() })
const render = () => act(async () => root.render(<AppProvider><FeedbackPage /></AppProvider>))
test('empty state is honest, modal opens and feature voting requests login', async () => {
  await render()
  expect(container.textContent).toContain('No reviews yet.')
  expect(container.textContent).not.toContain('average')
  const dialog = container.querySelector('dialog'); dialog.showModal = jest.fn()
  await act(async () => container.querySelector('header button').click())
  expect(dialog.showModal).toHaveBeenCalled()
  getPublicFeedback.mockResolvedValue({ items: [feature], has_more: false })
  await act(async () => container.querySelector('#tab-feature').click())
  expect(container.querySelector('.feedbackCard h2').textContent).toBe('<script>unsafe()</script>')
  expect(container.querySelector('script')).toBeNull()
  const login = container.querySelector('a[href="/#login"]')
  expect(login.textContent).toContain('Sign in to vote')
  await act(async () => login.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })))
  expect(sessionStorage.getItem('careerflow-auth-return')).toBe('/feedback')
  expect(voteFeedback).not.toHaveBeenCalled()
})
test('signed-in votes toggle, use server counts and developer reviews are labeled', async () => {
  useAuth.mockReturnValue({ user: { id: 'signed-in' } })
  getPublicFeedback.mockResolvedValue({ items: [{ ...feature, developer_feedback: true }], has_more: false })
  await render()
  await act(async () => container.querySelector('#tab-feature').click())
  expect(container.textContent).toContain('Developer feedback')
  voteFeedback.mockResolvedValue({ votes: 1, voted: true })
  await act(async () => container.querySelector('.featureActions button').click())
  expect(voteFeedback).toHaveBeenLastCalledWith('feature-id', true)
  expect(container.textContent).toContain('1 votes')
  expect(container.querySelector('.featureActions button').textContent).toBe('Remove vote')
  voteFeedback.mockResolvedValue({ votes: 0, voted: false })
  await act(async () => container.querySelector('.featureActions button').click())
  expect(voteFeedback).toHaveBeenLastCalledWith('feature-id', false)
  expect(container.textContent).toContain('0 votes')
})
test('load failures are retryable and do not look like an empty community', async () => {
  getPublicFeedback.mockRejectedValueOnce(new Error('private-detail'))
  await render()
  expect(container.textContent).toContain('Could not load feedback')
  expect(container.textContent).not.toContain('No reviews yet')
  expect(container.textContent).not.toContain('private-detail')
  await act(async () => container.querySelector('[role="alert"] button').click())
  expect(container.textContent).toContain('No reviews yet')
})
