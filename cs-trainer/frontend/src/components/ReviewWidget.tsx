import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

interface ReviewItem {
  question_id: string
  question_text: string
  part: string
  last_score: number
  next_review_at: string
}

export default function ReviewWidget() {
  const [items, setItems] = useState<ReviewItem[]>([])
  const navigate = useNavigate()

  useEffect(() => {
    axios.get('/api/questions/review').then(r => setItems(r.data)).catch(() => {})
  }, [])

  if (items.length === 0)
    return (
      <div className="bg-gray-800 rounded-xl p-5 border border-gray-700 text-center text-gray-500 text-sm">
        오늘 복습할 문제가 없습니다.
      </div>
    )

  return (
    <div className="bg-gray-800 rounded-xl p-5 border border-indigo-800 space-y-3">
      <h3 className="text-indigo-400 font-semibold text-sm">오늘의 복습 ({items.length})</h3>
      {items.slice(0, 3).map(item => (
        <button
          key={item.question_id}
          onClick={() => navigate(`/interview?question_id=${item.question_id}`)}
          className="w-full text-left bg-gray-700 hover:bg-gray-600 rounded-lg p-3 text-sm text-gray-200 transition-colors"
        >
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs text-indigo-400">{item.part}</span>
            <span className={`text-xs font-bold ${item.last_score >= 7 ? 'text-green-400' : 'text-red-400'}`}>
              이전 {item.last_score}점
            </span>
          </div>
          {item.question_text.slice(0, 60)}...
        </button>
      ))}
      {items.length > 3 && (
        <p className="text-xs text-gray-500 text-center">+ {items.length - 3}개 더</p>
      )}
    </div>
  )
}
