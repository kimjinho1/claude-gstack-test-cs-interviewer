import { useEffect, useState } from 'react'
import api from '../lib/api'
import { v4 as uuidv4 } from 'uuid'
import QuestionCard from '../components/QuestionCard'
import VoiceRecorder from '../components/VoiceRecorder'
import EvalResult from '../components/EvalResult'

interface Question { question_id: string; question_text: string; part: string }
interface EvalData { score: number; feedback: string; missed_points: string[]; follow_up_question: string | null }

type Phase = 'select' | 'question' | 'evaluating' | 'result' | 'followup'

export default function Interview() {
  const [parts, setParts] = useState<string[]>([])
  const [questions, setQuestions] = useState<Question[]>([])
  const [currentQ, setCurrentQ] = useState<Question | null>(null)
  const [phase, setPhase] = useState<Phase>('select')
  const [evalData, setEvalData] = useState<EvalData | null>(null)
  const [followUpQuestion, setFollowUpQuestion] = useState<string | null>(null)
  const [followUpCount, setFollowUpCount] = useState(0)
  const [sessionId] = useState(() => uuidv4())
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get('/api/questions/parts').then(r => setParts(r.data))
  }, [])

  const loadQuestions = async (part: string) => {
    const r = await api.get('/api/questions/', { params: { part } })
    setQuestions(r.data)
    const q = r.data[Math.floor(Math.random() * r.data.length)]
    setCurrentQ(q)
    setPhase('question')
    setEvalData(null)
    setFollowUpCount(0)
    setFollowUpQuestion(null)
    setError(null)
  }

  const handleAnswer = async (transcript: string) => {
    if (!currentQ) return
    setPhase('evaluating')
    setError(null)
    try {
      const { data } = await api.post('/api/evaluate', {
        session_id: sessionId,
        question_id: currentQ.question_id,
        question_text: currentQ.question_text,
        transcript,
        follow_up_count: followUpCount,
      })
      setEvalData(data)
      if (data.follow_up_question && followUpCount < 2) {
        setFollowUpQuestion(data.follow_up_question)
        setPhase('result')
      } else {
        setPhase('result')
      }
    } catch (e: any) {
      const msg = e.response?.data?.detail?.message || 'AI 평가에 실패했습니다. 다시 시도해주세요.'
      setError(msg)
      setPhase('question')
    }
  }

  const handleFollowUp = () => {
    if (!followUpQuestion) return
    setCurrentQ(prev => prev ? { ...prev, question_text: followUpQuestion } : prev)
    setFollowUpCount(c => c + 1)
    setFollowUpQuestion(null)
    setEvalData(null)
    setPhase('question')
  }

  const nextQuestion = () => {
    const q = questions[Math.floor(Math.random() * questions.length)]
    setCurrentQ(q)
    setPhase('question')
    setEvalData(null)
    setFollowUpCount(0)
    setFollowUpQuestion(null)
  }

  if (phase === 'select')
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold">인터뷰 모드</h2>
        <p className="text-gray-400">주제를 선택하세요</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {parts.map(part => (
            <button
              key={part}
              onClick={() => loadQuestions(part)}
              className="bg-gray-800 hover:bg-gray-700 border border-gray-700 hover:border-indigo-600 rounded-xl p-4 text-sm font-medium transition-all"
            >
              {part}
            </button>
          ))}
        </div>
      </div>
    )

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">인터뷰 모드</h2>
        <button onClick={() => setPhase('select')} className="text-sm text-gray-400 hover:text-gray-200">← 주제 변경</button>
      </div>
      {currentQ && <QuestionCard question={currentQ.question_text} questionId={currentQ.question_id} part={currentQ.part} onAutoSpeak />}
      {error && <div className="bg-red-900/40 border border-red-700 rounded-lg p-4 text-red-300 text-sm">{error}</div>}
      {(phase === 'question') && <VoiceRecorder onSubmit={handleAnswer} />}
      {phase === 'evaluating' && <div className="text-center text-gray-400 py-8 animate-pulse">AI가 평가 중...</div>}
      {phase === 'result' && evalData && (
        <div className="space-y-4">
          <EvalResult {...evalData} missedPoints={evalData.missed_points} followUpQuestion={null} />
          <div className="flex gap-3">
            {evalData.follow_up_question && followUpCount < 2 && (
              <button onClick={handleFollowUp} className="flex-1 py-3 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold">심화 질문 답변</button>
            )}
            <button onClick={nextQuestion} className="flex-1 py-3 rounded-lg bg-gray-700 hover:bg-gray-600 text-white font-semibold">다음 질문</button>
          </div>
        </div>
      )}
    </div>
  )
}
