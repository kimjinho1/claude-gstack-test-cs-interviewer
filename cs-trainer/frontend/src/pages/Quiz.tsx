import { useEffect, useState } from 'react'
import api from '../lib/api'
import QuestionCard from '../components/QuestionCard'
import VoiceRecorder from '../components/VoiceRecorder'
import EvalResult from '../components/EvalResult'
import ScoreBar from '../components/ScoreBar'

interface Question { question_id: string; question_text: string; part: string }
interface EvalData { score: number; feedback: string; missed_points: string[]; follow_up_question: string | null }

export default function Quiz() {
  const [parts, setParts] = useState<string[]>([])
  const [questions, setQuestions] = useState<Question[]>([])
  const [current, setCurrent] = useState(0)
  const [results, setResults] = useState<{ question: Question; eval: EvalData }[]>([])
  const [phase, setPhase] = useState<'select' | 'quiz' | 'evaluating' | 'result' | 'done'>('select')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { api.get('/api/questions/parts').then(r => setParts(r.data)) }, [])

  const startQuiz = async (part: string) => {
    const [r, sessionRes] = await Promise.all([
      api.get('/api/questions/', { params: { part } }),
      api.post('/api/history/', { mode: 'quiz', topic: part }),
    ])
    setSessionId(sessionRes.data.id)
    const shuffled = [...r.data].sort(() => Math.random() - 0.5).slice(0, 10)
    setQuestions(shuffled)
    setCurrent(0)
    setResults([])
    setPhase('quiz')
  }

  const handleAnswer = async (transcript: string) => {
    const q = questions[current]
    setPhase('evaluating')
    setError(null)
    try {
      const { data } = await api.post('/api/evaluate', {
        session_id: sessionId,
        question_id: q.question_id,
        question_text: q.question_text,
        transcript,
        follow_up_count: 0,
      })
      setResults(prev => [...prev, { question: q, eval: data }])
      setPhase('result')
    } catch (e: any) {
      setError(e.response?.data?.detail?.message || '평가 실패')
      setPhase('quiz')
    }
  }

  const next = async () => {
    if (current + 1 >= questions.length) {
      const avg = results.reduce((s, r) => s + r.eval.score, 0) / results.length
      if (sessionId) await api.patch(`/api/history/${sessionId}`, { total_score: avg })
      setPhase('done')
    } else {
      setCurrent(c => c + 1)
      setPhase('quiz')
    }
  }

  if (phase === 'select')
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold">퀴즈 모드</h2>
        <p className="text-gray-400">주제를 선택하면 10문제가 시작됩니다</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {parts.map(p => (
            <button key={p} onClick={() => startQuiz(p)} className="bg-gray-800 hover:bg-gray-700 border border-gray-700 hover:border-purple-600 rounded-xl p-4 text-sm font-medium transition-all">{p}</button>
          ))}
        </div>
      </div>
    )

  if (phase === 'done')
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold">퀴즈 완료</h2>
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <p className="text-gray-400 mb-2">평균 점수</p>
          <ScoreBar score={Math.round(results.reduce((s, r) => s + r.eval.score, 0) / results.length)} />
        </div>
        {results.map((r, i) => (
          <div key={i} className="space-y-2">
            <p className="text-sm font-semibold text-gray-400">Q{i+1}. {r.question.question_text.slice(0, 60)}...</p>
            <EvalResult score={r.eval.score} feedback={r.eval.feedback} missedPoints={r.eval.missed_points} />
          </div>
        ))}
        <button onClick={() => setPhase('select')} className="w-full py-3 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-semibold">다시 시작</button>
      </div>
    )

  return (
    <div className="space-y-5">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">퀴즈 모드</h2>
        <span className="text-sm text-gray-400">{current + 1} / {questions.length}</span>
      </div>
      <div className="w-full bg-gray-700 rounded-full h-1.5">
        <div className="bg-purple-500 h-1.5 rounded-full transition-all" style={{ width: `${(current / questions.length) * 100}%` }} />
      </div>
      {questions[current] && <QuestionCard question={questions[current].question_text} questionId={questions[current].question_id} part={questions[current].part} onAutoSpeak />}
      {error && <div className="bg-red-900/40 border border-red-700 rounded-lg p-4 text-red-300 text-sm">{error}</div>}
      {phase === 'quiz' && <VoiceRecorder onSubmit={handleAnswer} />}
      {phase === 'evaluating' && <div className="text-center text-gray-400 py-8 animate-pulse">AI가 평가 중...</div>}
      {phase === 'result' && results[results.length - 1] && (
        <div className="space-y-4">
          <EvalResult {...results[results.length-1].eval} missedPoints={results[results.length-1].eval.missed_points} />
          <button onClick={next} className="w-full py-3 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-semibold">
            {current + 1 >= questions.length ? '결과 보기' : '다음 문제'}
          </button>
        </div>
      )}
    </div>
  )
}
