import { NavLink, Outlet } from 'react-router-dom'

interface Props {
  onLogout: () => Promise<void>
}

export default function Layout({ onLogout }: Props) {
  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.logo}>あまおとちゃん</h1>
        <button onClick={onLogout} style={styles.logoutButton}>ログアウト</button>
      </header>
      <nav style={styles.nav}>
        <NavLink to="/admin/practice" style={({ isActive }) => ({...styles.navLink, ...(isActive ? styles.navLinkActive : {})})}>
          練習予定
        </NavLink>
        <NavLink to="/admin/reminder" style={({ isActive }) => ({...styles.navLink, ...(isActive ? styles.navLinkActive : {})})}>
          リマインダー
        </NavLink>
        <NavLink to="/admin/settings" style={({ isActive }) => ({...styles.navLink, ...(isActive ? styles.navLinkActive : {})})}>
          Bot 設定
        </NavLink>
        <NavLink to="/admin/general-settings" style={({ isActive }) => ({...styles.navLink, ...(isActive ? styles.navLinkActive : {})})}>
          設定管理
        </NavLink>
      </nav>
      <main style={styles.main}>
        <Outlet />
      </main>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#f5f5f5',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '0.75rem 1rem',
    backgroundColor: '#2d3748',
    color: '#fff',
  },
  logo: {
    fontSize: '1.125rem',
    margin: 0,
    fontWeight: 700,
  },
  logoutButton: {
    padding: '0.375rem 0.75rem',
    backgroundColor: 'transparent',
    color: '#e2e8f0',
    border: '1px solid #e2e8f0',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.875rem',
  },
  nav: {
    display: 'flex',
    gap: '0',
    backgroundColor: '#fff',
    borderBottom: '1px solid #e2e8f0',
    overflowX: 'auto' as const,
  },
  navLink: {
    padding: '0.75rem 1.25rem',
    textDecoration: 'none',
    color: '#718096',
    fontSize: '0.875rem',
    fontWeight: 500,
    borderBottom: '2px solid transparent',
    whiteSpace: 'nowrap' as const,
  },
  navLinkActive: {
    color: '#4299e1',
    borderBottomColor: '#4299e1',
  },
  main: {
    padding: '1rem',
    maxWidth: '1024px',
    margin: '0 auto',
  },
}
