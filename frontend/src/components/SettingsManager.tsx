import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { PracticeDefault } from '../types'

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: '16px',
    background: '#f7fafc',
    minHeight: '100vh',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: 700,
    color: '#333',
    marginBottom: '12px',
    paddingBottom: '8px',
    borderBottom: '2px solid #e2e8f0',
  },
  card: {
    background: '#fff',
    borderRadius: '8px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    padding: '16px',
    marginBottom: '16px',
  },
  tabBar: {
    display: 'flex',
    gap: '0',
    borderBottom: '2px solid #e2e8f0',
    marginBottom: '20px',
  },
  tab: {
    padding: '10px 20px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 600,
    color: '#718096',
    background: 'none',
    border: 'none',
    borderBottom: '2px solid transparent',
    marginBottom: '-2px',
    transition: 'color 0.15s',
  },
  tabActive: {
    color: '#4299e1',
    borderBottomColor: '#4299e1',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '4px',
    marginBottom: '10px',
  },
  label: {
    fontSize: '13px',
    color: '#718096',
    fontWeight: 600,
  },
  input: {
    border: '1px solid #e2e8f0',
    borderRadius: '4px',
    padding: '6px 10px',
    fontSize: '14px',
    color: '#333',
    outline: 'none',
    background: '#fff',
  },
  inputRow: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
    marginBottom: '12px',
  },
  memberItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 12px',
    background: '#f7fafc',
    borderRadius: '4px',
    border: '1px solid #e2e8f0',
    marginBottom: '6px',
  },
  memberName: {
    fontSize: '14px',
    color: '#333',
  },
  submitButton: {
    background: '#48bb78',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    padding: '7px 18px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 600,
  },
  addButton: {
    background: '#4299e1',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    padding: '7px 14px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 600,
    whiteSpace: 'nowrap' as const,
  },
  deleteButton: {
    background: '#fc8181',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    padding: '3px 10px',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: 600,
  },
  errorMsg: {
    color: '#fc8181',
    fontSize: '14px',
    padding: '8px',
    background: '#fff5f5',
    borderRadius: '4px',
    marginBottom: '12px',
  },
  successMsg: {
    color: '#276749',
    fontSize: '14px',
    padding: '8px',
    background: '#c6f6d5',
    borderRadius: '4px',
    marginBottom: '12px',
  },
  loadingMsg: {
    color: '#718096',
    padding: '16px',
    textAlign: 'center' as const,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    fontSize: '14px',
  },
  th: {
    textAlign: 'left' as const,
    padding: '8px 10px',
    background: '#f7fafc',
    borderBottom: '2px solid #e2e8f0',
    fontWeight: 600,
    color: '#718096',
    fontSize: '12px',
  },
  td: {
    padding: '8px 10px',
    borderBottom: '1px solid #e2e8f0',
    color: '#333',
  },
  thCenter: {
    textAlign: 'center' as const,
    padding: '8px 10px',
    background: '#f7fafc',
    borderBottom: '2px solid #e2e8f0',
    fontWeight: 600,
    color: '#718096',
    fontSize: '12px',
  },
  tdCenter: {
    padding: '8px 10px',
    borderBottom: '1px solid #e2e8f0',
    color: '#333',
    textAlign: 'center' as const,
  },
  tableInput: {
    border: '1px solid #e2e8f0',
    borderRadius: '4px',
    padding: '4px 8px',
    fontSize: '13px',
    color: '#333',
    outline: 'none',
    background: '#fff',
    width: '100%',
    boxSizing: 'border-box' as const,
  },
  keyLabel: {
    fontSize: '13px',
    color: '#4299e1',
    fontFamily: 'monospace',
    fontWeight: 600,
  },
  specialLabel: {
    fontSize: '13px',
    color: '#805ad5',
    fontFamily: 'monospace',
    fontWeight: 700,
  },
  formActions: {
    display: 'flex',
    gap: '8px',
    marginTop: '12px',
  },
}

const MONTH_NAMES = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']

// --- Members Tab ---
function MembersTab() {
  const [members, setMembers] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [newMember, setNewMember] = useState('')
  const [saving, setSaving] = useState(false)

  const fetchMembers = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getMembers()
      setMembers(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : '取得に失敗しました')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMembers()
  }, [fetchMembers])

  const handleAdd = () => {
    const trimmed = newMember.trim()
    if (!trimmed || members.includes(trimmed)) return
    setMembers(prev => [...prev, trimmed])
    setNewMember('')
    setSuccess(null)
  }

  const handleDelete = (name: string) => {
    setMembers(prev => prev.filter(m => m !== name))
    setSuccess(null)
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      await api.updateMembers(members)
      setSuccess('保存しました')
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存に失敗しました')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div style={styles.loadingMsg}>読み込み中...</div>

  return (
    <div>
      {error && <div style={styles.errorMsg}>{error}</div>}
      {success && <div style={styles.successMsg}>{success}</div>}
      <div style={styles.inputRow}>
        <input
          style={{ ...styles.input, flex: 1 }}
          type="text"
          placeholder="メンバー名を入力"
          value={newMember}
          onChange={e => setNewMember(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleAdd()}
        />
        <button style={styles.addButton} onClick={handleAdd}>
          追加
        </button>
      </div>
      {members.length === 0 ? (
        <div style={{ color: '#718096', padding: '12px 0', fontSize: '14px' }}>メンバーが登録されていません</div>
      ) : (
        members.map(name => (
          <div key={name} style={styles.memberItem}>
            <span style={styles.memberName}>{name}</span>
            <button style={styles.deleteButton} onClick={() => handleDelete(name)}>
              削除
            </button>
          </div>
        ))
      )}
      <div style={styles.formActions}>
        <button style={styles.submitButton} onClick={handleSave} disabled={saving}>
          {saving ? '保存中...' : '保存'}
        </button>
      </div>
    </div>
  )
}

// --- Practice Defaults Tab ---
function PracticeDefaultsTab() {
  const [defaults, setDefaults] = useState<PracticeDefault[]>(() =>
    Array.from({ length: 12 }, (_, i) => ({
      month: i + 1,
      enabled: false,
      place: '',
      start_time: '',
      end_time: '',
    }))
  )
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const fetchDefaults = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getPracticeDefaults()
      // Merge fetched data into the 12-month array
      setDefaults(prev =>
        prev.map(row => {
          const found = data.find(d => d.month === row.month)
          return found ? { ...row, ...found } : row
        })
      )
    } catch (e) {
      setError(e instanceof Error ? e.message : '取得に失敗しました')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchDefaults()
  }, [fetchDefaults])

  const updateRow = (month: number, field: keyof PracticeDefault, value: string | boolean) => {
    setDefaults(prev =>
      prev.map(row => (row.month === month ? { ...row, [field]: value } : row))
    )
    setSuccess(null)
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      await api.updatePracticeDefaults(defaults)
      setSuccess('保存しました')
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存に失敗しました')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div style={styles.loadingMsg}>読み込み中...</div>

  return (
    <div>
      {error && <div style={styles.errorMsg}>{error}</div>}
      {success && <div style={styles.successMsg}>{success}</div>}
      <div style={{ overflowX: 'auto' }}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>月</th>
              <th style={styles.thCenter}>有効</th>
              <th style={styles.th}>場所</th>
              <th style={styles.th}>開始</th>
              <th style={styles.th}>終了</th>
            </tr>
          </thead>
          <tbody>
            {defaults.map(row => (
              <tr key={row.month}>
                <td style={{ ...styles.td, fontWeight: 600, color: '#4299e1', width: '50px' }}>
                  {MONTH_NAMES[row.month - 1]}
                </td>
                <td style={styles.tdCenter}>
                  <input
                    type="checkbox"
                    checked={row.enabled}
                    onChange={e => updateRow(row.month, 'enabled', e.target.checked)}
                    style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                  />
                </td>
                <td style={styles.td}>
                  <input
                    style={styles.tableInput}
                    type="text"
                    value={row.place}
                    placeholder="場所"
                    onChange={e => updateRow(row.month, 'place', e.target.value)}
                  />
                </td>
                <td style={styles.td}>
                  <input
                    style={{ ...styles.tableInput, width: '90px' }}
                    type="time"
                    value={row.start_time}
                    onChange={e => updateRow(row.month, 'start_time', e.target.value)}
                  />
                </td>
                <td style={styles.td}>
                  <input
                    style={{ ...styles.tableInput, width: '90px' }}
                    type="time"
                    value={row.end_time}
                    onChange={e => updateRow(row.month, 'end_time', e.target.value)}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={styles.formActions}>
        <button style={styles.submitButton} onClick={handleSave} disabled={saving}>
          {saving ? '保存中...' : '保存'}
        </button>
      </div>
    </div>
  )
}

// --- App Settings Tab ---
function AppSettingsTab() {
  const [settings, setSettings] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const fetchSettings = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getAppSettings()
      setSettings(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : '取得に失敗しました')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchSettings()
  }, [fetchSettings])

  const updateValue = (key: string, value: string) => {
    setSettings(prev => ({ ...prev, [key]: value }))
    setSuccess(null)
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      await api.updateAppSettings(settings)
      setSuccess('保存しました')
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存に失敗しました')
    } finally {
      setSaving(false)
    }
  }

  const getLabel = (key: string): string => {
    const labels: Record<string, string> = {
      default_remind_date: 'リマインドデフォルト日数',
    }
    return labels[key] ?? key
  }

  const isSpecial = (key: string) => key === 'default_remind_date'

  if (loading) return <div style={styles.loadingMsg}>読み込み中...</div>

  const keys = Object.keys(settings)

  return (
    <div>
      {error && <div style={styles.errorMsg}>{error}</div>}
      {success && <div style={styles.successMsg}>{success}</div>}
      {keys.length === 0 ? (
        <div style={{ color: '#718096', padding: '12px 0', fontSize: '14px' }}>設定がありません</div>
      ) : (
        keys.map(key => (
          <div key={key} style={styles.formGroup}>
            <label style={isSpecial(key) ? styles.specialLabel : styles.keyLabel}>
              {getLabel(key)}
              {isSpecial(key) && (
                <span style={{ fontSize: '11px', fontWeight: 400, color: '#718096', marginLeft: '8px', fontFamily: 'sans-serif' }}>
                  (default_remind_date)
                </span>
              )}
            </label>
            <input
              style={styles.input}
              type="text"
              value={settings[key]}
              onChange={e => updateValue(key, e.target.value)}
            />
          </div>
        ))
      )}
      <div style={styles.formActions}>
        <button style={styles.submitButton} onClick={handleSave} disabled={saving}>
          {saving ? '保存中...' : '保存'}
        </button>
      </div>
    </div>
  )
}

// --- Main component ---
type TabId = 'members' | 'practice-defaults' | 'app-settings'

const TABS: { id: TabId; label: string }[] = [
  { id: 'members', label: 'メンバー管理' },
  { id: 'practice-defaults', label: '練習デフォルト' },
  { id: 'app-settings', label: 'アプリ設定' },
]

export default function SettingsManager() {
  const [activeTab, setActiveTab] = useState<TabId>('members')

  return (
    <div style={styles.container}>
      <h2 style={styles.sectionTitle}>設定管理</h2>
      <div style={styles.card}>
        <div style={styles.tabBar}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              style={{
                ...styles.tab,
                ...(activeTab === tab.id ? styles.tabActive : {}),
              }}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        {activeTab === 'members' && <MembersTab />}
        {activeTab === 'practice-defaults' && <PracticeDefaultsTab />}
        {activeTab === 'app-settings' && <AppSettingsTab />}
      </div>
    </div>
  )
}
