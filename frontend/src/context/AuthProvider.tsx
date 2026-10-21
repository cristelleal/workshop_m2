import { useEffect, useState, type ReactNode } from 'react'
import { clearToken, getToken } from '../services/api'
import { getMe, login, register, type User } from '../services/auth'
import { AuthContext } from './AuthContext'

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(Boolean(getToken()))

  // Un token est déjà enregistré : on récupère l'utilisateur, ou on l'oublie s'il a expiré.
  useEffect(() => {
    if (!getToken()) return
    getMe()
      .then(setUser)
      .catch(clearToken)
      .finally(() => setLoading(false))
  }, [])

  const signIn = async (email: string, password: string) => {
    await login(email, password)
    setUser(await getMe())
  }

  const signUp = async (email: string, password: string) => {
    await register(email, password)
    await signIn(email, password)
  }

  const signOut = () => {
    clearToken()
    setUser(null)
  }

  return <AuthContext value={{ user, loading, signIn, signUp, signOut }}>{children}</AuthContext>
}
