import { useEffect } from 'react'
import { useTTS } from '../hooks/useTTS'

interface Props {
  question: string
  questionId: string
  part: string
  onAutoSpeak?: boolean
}

export default function QuestionCard({ question, questionId, part, onAutoSpeak }: Props) {
  const { speak, cancel, enabled, toggle, isSupported } = useTTS()

  useEffect(() => {
    if (onAutoSpeak && enabled) speak(question)
    return () => cancel()
  }, [questionId])

  return (
    <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
      <div className="flex justify-between items-start mb-3">
        <span className="text-xs text-indigo-400 font-mono bg-indigo-900/30 px-2 py-1 rounded">{part}</span>
        {isSupported && (
          <button
            onClick={() => enabled ? (cancel(), speak(question)) : toggle()}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors flex items-center gap-1"
          >
            {enabled ? '🔊' : '🔇'} TTS
          </button>
        )}
      </div>
      <p className="text-gray-100 text-base leading-relaxed font-medium">{question}</p>
    </div>
  )
}
