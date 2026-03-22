import { useState } from 'react'
import { useSpeechRecognition } from '../hooks/useSpeechRecognition'

interface Props {
  onSubmit: (text: string) => void
  disabled?: boolean
}

export default function VoiceRecorder({ onSubmit, disabled }: Props) {
  const { transcript, isListening, isSupported, start, stop, reset } = useSpeechRecognition()
  const [textInput, setTextInput] = useState('')
  const useText = !isSupported

  const handleSubmit = () => {
    const answer = useText ? textInput.trim() : transcript.trim()
    if (!answer) return
    onSubmit(answer)
    reset()
    setTextInput('')
  }

  return (
    <div className="space-y-3">
      {!isSupported && (
        <p className="text-xs text-yellow-400">브라우저가 음성 인식을 지원하지 않아 텍스트로 입력합니다.</p>
      )}
      {isSupported ? (
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700 min-h-[80px]">
          {transcript || <span className="text-gray-500 text-sm">답변이 여기에 표시됩니다...</span>}
        </div>
      ) : (
        <textarea
          className="w-full bg-gray-800 rounded-xl p-4 border border-gray-700 text-gray-100 resize-none min-h-[80px] focus:outline-none focus:border-indigo-500"
          placeholder="답변을 입력하세요..."
          value={textInput}
          onChange={e => setTextInput(e.target.value)}
          disabled={disabled}
        />
      )}
      <div className="flex gap-3">
        {isSupported && (
          <>
            <button
              onClick={isListening ? stop : start}
              disabled={disabled}
              className={`flex-1 py-3 rounded-lg font-semibold transition-colors ${
                isListening
                  ? 'bg-red-600 hover:bg-red-700 text-white animate-pulse'
                  : 'bg-indigo-600 hover:bg-indigo-700 text-white'
              } disabled:opacity-50`}
            >
              {isListening ? '녹음 중지' : '녹음 시작'}
            </button>
            {transcript && <button onClick={reset} className="px-4 py-3 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-300 text-sm">초기화</button>}
          </>
        )}
        <button
          onClick={handleSubmit}
          disabled={disabled || (!transcript && !textInput)}
          className="flex-1 py-3 rounded-lg bg-green-600 hover:bg-green-700 text-white font-semibold transition-colors disabled:opacity-50"
        >
          제출
        </button>
      </div>
    </div>
  )
}
