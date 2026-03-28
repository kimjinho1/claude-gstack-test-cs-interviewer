import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useTTS } from '../hooks/useTTS'

const mockSpeak = vi.fn()
const mockCancel = vi.fn()

beforeEach(() => {
  localStorage.clear()
  vi.stubGlobal('speechSynthesis', { speak: mockSpeak, cancel: mockCancel })
  vi.stubGlobal('SpeechSynthesisUtterance', class {
    text: string; lang = ''; rate = 1; pitch = 1; volume = 1
    constructor(text: string) { this.text = text }
  })
  mockSpeak.mockClear()
  mockCancel.mockClear()
})

describe('useTTS', () => {
  it('defaults to enabled', () => {
    const { result } = renderHook(() => useTTS())
    expect(result.current.enabled).toBe(true)
  })

  it('persists disabled state to localStorage', () => {
    const { result } = renderHook(() => useTTS())
    act(() => result.current.toggle())
    expect(localStorage.getItem('tts_enabled')).toBe('false')
  })

  it('restores from localStorage', () => {
    localStorage.setItem('tts_enabled', 'false')
    const { result } = renderHook(() => useTTS())
    expect(result.current.enabled).toBe(false)
  })

  it('speaks with ko-KR for Korean text', () => {
    const { result } = renderHook(() => useTTS())
    act(() => result.current.speak('TCP란 무엇인가?'))
    expect(mockSpeak).toHaveBeenCalled()
    const utterance = mockSpeak.mock.calls[0][0]
    expect(utterance.lang).toBe('ko-KR')
  })

  it('does not speak when disabled', () => {
    localStorage.setItem('tts_enabled', 'false')
    const { result } = renderHook(() => useTTS())
    act(() => result.current.speak('test'))
    expect(mockSpeak).not.toHaveBeenCalled()
  })
})
