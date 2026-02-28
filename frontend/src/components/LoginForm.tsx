import { useState, type FormEvent } from 'react'

interface Props {
  onLogin: (token: string) => Promise<void>
}

export default function LoginForm({ onLogin }: Props) {
  const [token, setToken] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await onLogin(token)
    } catch {
      setError('認証に失敗しました')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>あまおとちゃん 管理画面</h1>
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="管理トークンを入力"
            style={styles.input}
            required
          />
          {error && <p style={styles.error}>{error}</p>}
          <button type="submit" disabled={loading} style={styles.button}>
            {loading ? 'ログイン中...' : 'ログイン'}
          </button>
        </form>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    backgroundColor: '#f5f5f5',
  },
  card: {
    backgroundColor: '#fff',
    padding: '2rem',
    borderRadius: '8px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    width: '100%',
    maxWidth: '400px',
    margin: '1rem',
  },
  title: {
    fontSize: '1.5rem',
    textAlign: 'center' as const,
    marginBottom: '1.5rem',
    color: '#333',
  },
  input: {
    width: '100%',
    padding: '0.75rem',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '1rem',
    marginBottom: '1rem',
    boxSizing: 'border-box' as const,
  },
  error: {
    color: '#e53e3e',
    fontSize: '0.875rem',
    marginBottom: '0.5rem',
  },
  button: {
    width: '100%',
    padding: '0.75rem',
    backgroundColor: '#4299e1',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    fontSize: '1rem',
    cursor: 'pointer',
  },
}
