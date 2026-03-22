import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'tts_enabled'

export function useTTS() {
  const [enabled, setEnabled] = useState<boolean>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) !== 'false'
    } catch {
      return true
    }
  })

  const isSupported = typeof window !== 'undefined' && 'speechSynthesis' in window

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, String(enabled))
    } catch {}
  }, [enabled])

  const speak = useCallback((text: string) => {
    if (!enabled || !isSupported) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    // Detect language: if text contains Korean, use ko-KR, else en-US
    utterance.lang = /[가-힣]/.test(text) ? 'ko-KR' : 'en-US'
    utterance.rate = 0.9
    window.speechSynthesis.speak(utterance)
  }, [enabled, isSupported])

  const cancel = useCallback(() => {
    if (isSupported) window.speechSynthesis.cancel()
  }, [isSupported])

  const toggle = useCallback(() => setEnabled(v => !v), [])

  return { enabled, isSupported, speak, cancel, toggle }
}
