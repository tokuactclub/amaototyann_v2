import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'

export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const checkAuth = useCallback(async () => {
    try {
      await api.checkAuth()
      setIsAuthenticated(true)
    } catch {
      setIsAuthenticated(false)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  const login = async (token: string) => {
    await api.login(token)
    setIsAuthenticated(true)
  }

  const logout = async () => {
    await api.logout()
    setIsAuthenticated(false)
  }

  return { isAuthenticated, isLoading, login, logout, checkAuth }
}
