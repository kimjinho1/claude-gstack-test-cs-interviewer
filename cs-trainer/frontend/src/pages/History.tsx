import { useEffect, useState } from 'react'
import api from '../lib/api'
import RadarChart from '../components/RadarChart'
import TrendChart from '../components/TrendChart'

interface Session {
  id: string; mode: string; topic: string | null; total_score: number | null;
  created_at: string; question_count: number;
}

export default function History() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [stats, setStats] = useState<{ radar: { part: string; avg_score: number }[]; trend: { week: string; avg_score: number }[] }>({ radar: [], trend: [] })

  useEffect(() => {
    api.get('/api/history/').then(r => setSessions(r.data))
    api.get('/api/stats/').then(r => setStats(r.data))
  }, [])

  return (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold">히스토리</h2>
      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <h3 className="text-sm font-semibold text-gray-400 mb-4">파트별 실력</h3>
          <RadarChart data={stats.radar} />
        </div>
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <h3 className="text-sm font-semibold text-gray-400 mb-4">주차별 추세</h3>
          <TrendChart data={stats.trend} />
        </div>
      </div>
      <div className="space-y-3">
        <h3 className="text-lg font-semibold">세션 기록</h3>
        {sessions.length === 0 && <p className="text-gray-500 text-sm">아직 세션이 없습니다.</p>}
        {sessions.map(s => (
          <div key={s.id} className="bg-gray-800 rounded-xl p-4 border border-gray-700 flex items-center justify-between">
            <div>
              <span className={`text-xs px-2 py-0.5 rounded-full font-semibold mr-2 ${
                s.mode === 'interview' ? 'bg-indigo-900 text-indigo-300' :
                s.mode === 'quiz' ? 'bg-purple-900 text-purple-300' : 'bg-emerald-900 text-emerald-300'
              }`}>{s.mode}</span>
              <span className="text-sm text-gray-400">{s.topic || '혼합'}</span>
              <p className="text-xs text-gray-600 mt-1">{new Date(s.created_at).toLocaleString('ko-KR')}</p>
            </div>
            {s.total_score != null && (
              <div className="text-right">
                <span className={`text-2xl font-bold ${s.total_score >= 7 ? 'text-green-400' : 'text-red-400'}`}>
                  {s.total_score.toFixed(1)}
                </span>
                <p className="text-xs text-gray-500">{s.question_count}문제</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
