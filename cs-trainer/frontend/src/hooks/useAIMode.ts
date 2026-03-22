import { useState } from 'react'

export type AIMode = 'local' | 'cloud'

export function useAIMode() {
  const [mode, setMode] = useState<AIMode>(() =>
    (localStorage.getItem('ai_mode') as AIMode) || 'cloud'
  )
  const toggle = () => {
    const next: AIMode = mode === 'cloud' ? 'local' : 'cloud'
    setMode(next)
    localStorage.setItem('ai_mode', next)
  }
  return { mode, toggle }
}
