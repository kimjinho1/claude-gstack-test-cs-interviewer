import { Link } from 'react-router-dom'
import ReviewWidget from '../components/ReviewWidget'

const modes = [
  { to: '/interview', label: '인터뷰 모드', desc: '주제별 심층 면접 연습', icon: '🎤', color: 'border-indigo-700 hover:border-indigo-500' },
  { to: '/quiz', label: '퀴즈 모드', desc: '10문제 빠른 배치 평가', icon: '📝', color: 'border-purple-700 hover:border-purple-500' },
  { to: '/mock', label: '모의 면접', desc: '30분 실전 면접 시뮬레이션', icon: '⏱️', color: 'border-emerald-700 hover:border-emerald-500' },
]

export default function Home() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-100 mb-2">CS Interview Trainer</h1>
        <p className="text-gray-400">AI가 평가하는 나만의 CS 면접 코치</p>
      </div>
      <ReviewWidget />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {modes.map(({ to, label, desc, icon, color }) => (
          <Link
            key={to}
            to={to}
            className={`bg-gray-800 rounded-xl p-5 border-2 ${color} transition-colors group`}
          >
            <div className="text-3xl mb-3">{icon}</div>
            <h2 className="font-bold text-gray-100 mb-1">{label}</h2>
            <p className="text-sm text-gray-400">{desc}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}
