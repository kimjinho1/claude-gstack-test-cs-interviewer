import { Routes, Route, Link, useLocation, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Home from './pages/Home'
import Interview from './pages/Interview'
import Quiz from './pages/Quiz'
import Mock from './pages/Mock'
import History from './pages/History'
import Notes from './pages/Notes'
import Login from './pages/Login'

const navLinks = [
  { to: '/', label: '홈' },
  { to: '/interview', label: '인터뷰' },
  { to: '/quiz', label: '퀴즈' },
  { to: '/mock', label: '모의 면접' },
  { to: '/history', label: '히스토리' },
  { to: '/notes', label: '약점 노트' },
]

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="flex items-center justify-center h-screen text-gray-400">로딩 중...</div>
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AppLayout() {
  const { pathname } = useLocation()
  const { user, logout } = useAuth()

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
        {user && (
          <div className="ml-auto flex items-center gap-3">
            {user.avatar_url && (
              <img src={user.avatar_url} alt={user.name ?? ''} className="w-7 h-7 rounded-full" />
            )}
            <span className="text-sm text-gray-300">{user.name}</span>
            <button
              onClick={logout}
              className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
            >
              로그아웃
            </button>
          </div>
        )}
      </nav>
      <main className="flex-1 p-6 max-w-4xl mx-auto w-full">
        <Routes>
          <Route path="/" element={<ProtectedRoute><Home /></ProtectedRoute>} />
          <Route path="/interview" element={<ProtectedRoute><Interview /></ProtectedRoute>} />
          <Route path="/quiz" element={<ProtectedRoute><Quiz /></ProtectedRoute>} />
          <Route path="/mock" element={<ProtectedRoute><Mock /></ProtectedRoute>} />
          <Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
          <Route path="/notes" element={<ProtectedRoute><Notes /></ProtectedRoute>} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/*" element={<AppLayout />} />
      </Routes>
    </AuthProvider>
  )
}
