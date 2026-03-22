import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import api from '../lib/api'

interface User {
  id: string
  provider: string
  email: string | null
  name: string | null
  avatar_url: string | null
}

interface AuthContextType {
  user: User | null
  loading: boolean
  logout: () => void
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  logout: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // OAuth 콜백에서 ?token= 파라미터로 JWT 전달되는 경우 처리
    const params = new URLSearchParams(window.location.search)
    const tokenFromUrl = params.get('token')
    if (tokenFromUrl) {
      localStorage.setItem('auth_token', tokenFromUrl)
      params.delete('token')
      const newUrl = window.location.pathname + (params.toString() ? `?${params}` : '')
      window.history.replaceState({}, '', newUrl)
    }

    const token = localStorage.getItem('auth_token')
    if (!token) {
      setLoading(false)
      return
    }

    api.get('/api/auth/me')
      .then((r) => setUser(r.data))
      .catch(() => {
        localStorage.removeItem('auth_token')
      })
      .finally(() => setLoading(false))
  }, [])

  const logout = () => {
    localStorage.removeItem('auth_token')
    setUser(null)
    window.location.href = '/login'
  }

  return (
    <AuthContext.Provider value={{ user, loading, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
