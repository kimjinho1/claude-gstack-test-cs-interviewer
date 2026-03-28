import { useEffect, useState } from 'react'
import { useSpeechRecognition } from '../hooks/useSpeechRecognition'

interface Props {
  onSubmit: (text: string) => void
  disabled?: boolean
}

export default function VoiceRecorder({ onSubmit, disabled }: Props) {
  const { transcript, isListening, isSupported, start, stop, reset } = useSpeechRecognition()
  const [textValue, setTextValue] = useState('')

  // 음성 인식 결과가 바뀌면 textarea에 반영 (직접 편집도 가능)
  useEffect(() => {
    if (transcript) setTextValue(transcript)
  }, [transcript])

  const handleReset = () => {
    reset()
    setTextValue('')
  }

  const handleSubmit = () => {
    const answer = textValue.trim()
    if (!answer) return
    onSubmit(answer)
    handleReset()
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleSubmit()
  }

  return (
    <div className="space-y-3">
      {!isSupported && (
        <p className="text-xs text-yellow-400">브라우저가 음성 인식을 지원하지 않아 텍스트로만 입력합니다.</p>
      )}
      <textarea
        className="w-full bg-gray-800 rounded-xl p-4 border border-gray-700 text-gray-100 resize-none min-h-[100px] focus:outline-none focus:border-indigo-500 transition-colors"
        placeholder={
          isSupported
            ? '음성 녹음 후 자동으로 입력되거나, 직접 타이핑하세요... (Ctrl+Enter로 제출)'
            : '답변을 입력하세요... (Ctrl+Enter로 제출)'
        }
        value={textValue}
        onChange={e => setTextValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
      />
      <div className="flex gap-3">
        {isSupported && (
          <button
            onClick={isListening ? stop : start}
            disabled={disabled}
            className={`flex-1 py-3 rounded-lg font-semibold transition-colors ${
              isListening
                ? 'bg-red-600 hover:bg-red-700 text-white animate-pulse'
                : 'bg-indigo-600 hover:bg-indigo-700 text-white'
            } disabled:opacity-50`}
          >
            {isListening ? '🎙 녹음 중지' : '🎙 녹음 시작'}
          </button>
        )}
        {textValue && (
          <button
            onClick={handleReset}
            disabled={disabled}
            className="px-4 py-3 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-300 text-sm"
          >
            초기화
          </button>
        )}
        <button
          onClick={handleSubmit}
          disabled={disabled || !textValue.trim()}
          className="flex-1 py-3 rounded-lg bg-green-600 hover:bg-green-700 text-white font-semibold transition-colors disabled:opacity-50"
        >
          제출
        </button>
      </div>
    </div>
  )
}
