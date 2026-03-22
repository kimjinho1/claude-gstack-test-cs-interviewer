import { useEffect, useState } from 'react'
import axios from 'axios'

interface Note {
  id: number; question_id: string; topic: string;
  missed_points: string[]; last_score: number; review_count: number; updated_at: string;
}

export default function Notes() {
  const [notes, setNotes] = useState<Note[]>([])

  const load = () => axios.get('/api/notes/').then(r => setNotes(r.data))
  useEffect(() => { load() }, [])

  const deleteNote = async (id: number) => {
    await axios.delete(`/api/notes/${id}`)
    setNotes(notes.filter(n => n.id !== id))
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">약점 노트</h2>
      {notes.length === 0 && <p className="text-gray-500 text-sm">약점 노트가 없습니다. 점수 7점 미만 항목이 자동으로 여기에 기록됩니다.</p>}
      {notes.map(n => (
        <div key={n.id} className="bg-gray-800 rounded-xl p-5 border border-red-900/40">
          <div className="flex justify-between items-start mb-3">
            <div>
              <p className="font-medium text-gray-200">{n.question_id}</p>
              <p className="text-xs text-gray-500 mt-0.5">{n.topic} · {n.review_count}회 복습 · 최근 {n.last_score}점</p>
            </div>
            <button onClick={() => deleteNote(n.id)} className="text-gray-600 hover:text-red-400 text-sm transition-colors">✕</button>
          </div>
          {n.missed_points.length > 0 && (
            <ul className="space-y-1 mt-2">
              {n.missed_points.map((p, i) => (
                <li key={i} className="text-sm text-red-300 flex gap-2"><span>•</span>{p}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  )
}
