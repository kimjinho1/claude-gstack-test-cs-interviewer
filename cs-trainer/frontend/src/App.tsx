import { Routes, Route, Link, useLocation } from 'react-router-dom'
import Home from './pages/Home'
import Interview from './pages/Interview'
import Quiz from './pages/Quiz'
import Mock from './pages/Mock'
import History from './pages/History'
import Notes from './pages/Notes'

const navLinks = [
  { to: '/', label: '홈' },
  { to: '/interview', label: '인터뷰' },
  { to: '/quiz', label: '퀴즈' },
  { to: '/mock', label: '모의 면접' },
  { to: '/history', label: '히스토리' },
  { to: '/notes', label: '약점 노트' },
]

export default function App() {
  const { pathname } = useLocation()
  return (
    <div className="min-h-screen flex flex-col">
      <nav className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex gap-6 items-center">
        <span className="font-bold text-indigo-400 text-lg mr-4">CS Trainer</span>
        {navLinks.map(({ to, label }) => (
          <Link
            key={to}
            to={to}
            className={`text-sm transition-colors ${
              pathname === to ? 'text-indigo-400 font-semibold' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {label}
          </Link>
        ))}
      </nav>
      <main className="flex-1 p-6 max-w-4xl mx-auto w-full">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/interview" element={<Interview />} />
          <Route path="/quiz" element={<Quiz />} />
          <Route path="/mock" element={<Mock />} />
          <Route path="/history" element={<History />} />
          <Route path="/notes" element={<Notes />} />
        </Routes>
      </main>
    </div>
  )
}
