import { useEffect, useRef, useState } from 'react'
import api from '../lib/api'
import { v4 as uuidv4 } from 'uuid'
import QuestionCard from '../components/QuestionCard'
import VoiceRecorder from '../components/VoiceRecorder'
import EvalResult from '../components/EvalResult'
import ScoreBar from '../components/ScoreBar'

interface Question { question_id: string; question_text: string; part: string }
interface EvalData { score: number; feedback: string; missed_points: string[]; follow_up_question: string | null }

const MOCK_DURATION = 30 * 60 // 30 minutes in seconds

export default function Mock() {
  const [phase, setPhase] = useState<'idle' | 'running' | 'evaluating' | 'result' | 'done'>('idle')
  const [questions, setQuestions] = useState<Question[]>([])
  const [current, setCurrent] = useState(0)
  const [results, setResults] = useState<{ question: Question; eval: EvalData | null }[]>([])
  const [timeLeft, setTimeLeft] = useState(MOCK_DURATION)
  const [sessionId] = useState(() => uuidv4())
  const startTimeRef = useRef<number>(Date.now())
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const finishMock = async () => {
    if (timerRef.current) clearInterval(timerRef.current)
    const answered = results.filter(r => r.eval !== null)
    const avg = answered.length ? answered.reduce((s, r) => s + (r.eval?.score || 0), 0) / answered.length : 0
    const dur = Math.round((Date.now() - startTimeRef.current) / 1000)
    await api.post('/api/history/', { mode: 'mock', total_score: avg, duration_s: dur })
    setPhase('done')
  }

  const startMock = async () => {
    const r = await api.get('/api/questions/mock')
    setQuestions(r.data)
    setCurrent(0)
    setResults([])
    setTimeLeft(MOCK_DURATION)
    startTimeRef.current = Date.now()
    setPhase('running')
    timerRef.current = setInterval(() => {
      setTimeLeft(t => {
        if (t <= 1) {
          if (timerRef.current) clearInterval(timerRef.current)
          return 0
        }
        return t - 1
      })
    }, 1000)
  }

  const handleAnswer = async (transcript: string) => {
    const q = questions[current]
    setPhase('evaluating')
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
    } catch {
      setResults(prev => [...prev, { question: q, eval: null }])
      setPhase('result')
    }
  }

  const skipQuestion = () => {
    // Timer expired or user skips: no score recorded
    setResults(prev => [...prev, { question: questions[current], eval: null }])
    nextQuestion()
  }

  const nextQuestion = () => {
    if (current + 1 >= questions.length) finishMock()
    else { setCurrent(c => c + 1); setPhase('running') }
  }

  useEffect(() => () => { if (timerRef.current) clearInterval(timerRef.current) }, [])

  const fmt = (s: number) => `${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`

  if (phase === 'idle')
    return (
      <div className="space-y-6 text-center">
        <h2 className="text-2xl font-bold">모의 면접 모드</h2>
        <p className="text-gray-400">혼합 주제 8~10문제 · 30분 타이머<br/>실전처럼 대답하세요</p>
        <button onClick={startMock} className="px-8 py-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-lg transition-colors">면접 시작</button>
      </div>
    )

  if (phase === 'done') {
    const answered = results.filter(r => r.eval !== null)
    const avg = answered.length ? Math.round(answered.reduce((s, r) => s + (r.eval?.score || 0), 0) / answered.length) : 0
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold">모의 면접 완료</h2>
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <p className="text-gray-400 mb-1 text-sm">평균 점수 ({answered.length}/{results.length}문제 답변)</p>
          <ScoreBar score={avg} />
        </div>
        {results.map((r, i) => (
          <div key={i} className="space-y-2">
            <p className="text-sm text-gray-400">Q{i+1} · {r.question.part} · {r.question.question_text.slice(0,50)}...</p>
            {r.eval ? <EvalResult {...r.eval} missedPoints={r.eval.missed_points} /> : <div className="text-sm text-gray-500 bg-gray-800 rounded-lg p-3">시간 초과 — 건너뜀</div>}
          </div>
        ))}
        <button onClick={() => setPhase('idle')} className="w-full py-3 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold">다시 시작</button>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">모의 면접</h2>
        <div className="flex gap-4 items-center">
          <span className="text-sm text-gray-400">{current + 1}/{questions.length}</span>
          <span className={`font-mono text-lg font-bold ${timeLeft < 300 ? 'text-red-400' : 'text-emerald-400'}`}>{fmt(timeLeft)}</span>
        </div>
      </div>
      {questions[current] && <QuestionCard question={questions[current].question_text} questionId={questions[current].question_id} part={questions[current].part} onAutoSpeak />}
      {phase === 'running' && (
        <div className="space-y-3">
          <VoiceRecorder onSubmit={handleAnswer} />
          <button onClick={skipQuestion} className="w-full py-2 text-sm text-gray-500 hover:text-gray-400">이 문제 건너뛰기</button>
        </div>
      )}
      {phase === 'evaluating' && <div className="text-center text-gray-400 py-8 animate-pulse">AI가 평가 중...</div>}
      {phase === 'result' && results[results.length - 1]?.eval && (
        <div className="space-y-4">
          <EvalResult {...results[results.length-1].eval!} missedPoints={results[results.length-1].eval!.missed_points} />
          <button onClick={nextQuestion} className="w-full py-3 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold">
            {current + 1 >= questions.length ? '결과 보기' : '다음 문제'}
          </button>
        </div>
      )}
    </div>
  )
}
