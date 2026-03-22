import ScoreBar from './ScoreBar'

interface Props {
  score: number
  feedback: string
  missedPoints: string[]
  followUpQuestion?: string | null
}

export default function EvalResult({ score, feedback, missedPoints, followUpQuestion }: Props) {
  const passed = score >= 7
  return (
    <div className="bg-gray-800 rounded-xl p-5 space-y-4 border border-gray-700">
      <div className="flex items-center justify-between">
        <span className="font-semibold text-gray-300">평가 결과</span>
        <span className={`px-3 py-1 rounded-full text-sm font-bold ${passed ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}>
          {passed ? '합격' : '불합격'}
        </span>
      </div>
      <ScoreBar score={score} />
      <p className="text-gray-300 text-sm leading-relaxed">{feedback}</p>
      {missedPoints.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-2">놓친 포인트</p>
          <ul className="space-y-1">
            {missedPoints.map((p, i) => (
              <li key={i} className="text-sm text-red-300 flex gap-2">
                <span>•</span><span>{p}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {followUpQuestion && (
        <div className="bg-indigo-900/40 rounded-lg p-4 border border-indigo-700">
          <p className="text-xs text-indigo-400 mb-1 font-semibold">심화 질문</p>
          <p className="text-indigo-200 text-sm">{followUpQuestion}</p>
        </div>
      )}
    </div>
  )
}
