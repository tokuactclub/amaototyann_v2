import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import Layout from './components/Layout'
import LoginForm from './components/LoginForm'
import PracticeList from './components/PracticeList'
import ReminderList from './components/ReminderList'
import BotSettings from './components/BotSettings'
import SettingsManager from './components/SettingsManager'

function App() {
  const { isAuthenticated, isLoading, login, logout } = useAuth()

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', color: '#718096' }}>
        読み込み中...
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/admin/login" element={
          isAuthenticated
            ? <Navigate to="/admin/practice" replace />
            : <LoginForm onLogin={login} />
        } />
        {isAuthenticated ? (
          <Route element={<Layout onLogout={logout} />}>
            <Route path="/admin/practice" element={<PracticeList />} />
            <Route path="/admin/reminder" element={<ReminderList />} />
            <Route path="/admin/settings" element={<BotSettings />} />
            <Route path="/admin/general-settings" element={<SettingsManager />} />
            <Route path="/admin" element={<Navigate to="/admin/practice" replace />} />
            <Route path="*" element={<Navigate to="/admin/practice" replace />} />
          </Route>
        ) : (
          <Route path="*" element={<Navigate to="/admin/login" replace />} />
        )}
      </Routes>
    </BrowserRouter>
  )
}

export default App
