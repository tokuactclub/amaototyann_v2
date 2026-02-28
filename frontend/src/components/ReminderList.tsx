import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { ReminderEvent, ReminderCreateRequest } from '../types'

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: '16px',
    background: '#f7fafc',
    minHeight: '100vh',
  },
  card: {
    background: '#fff',
    borderRadius: '8px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    padding: '16px',
    marginBottom: '16px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
    flexWrap: 'wrap' as const,
    gap: '8px',
  },
  title: {
    fontSize: '20px',
    fontWeight: 700,
    color: '#333',
    margin: 0,
  },
  addButton: {
    background: '#4299e1',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    padding: '8px 16px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 600,
  },
  tableWrapper: {
    overflowX: 'auto' as const,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    fontSize: '14px',
  },
  th: {
    background: '#f7fafc',
    border: '1px solid #e2e8f0',
    padding: '8px 12px',
    textAlign: 'left' as const,
    color: '#718096',
    fontWeight: 600,
    whiteSpace: 'nowrap' as const,
  },
  td: {
    border: '1px solid #e2e8f0',
    padding: '8px 12px',
    color: '#333',
    verticalAlign: 'top' as const,
  },
  finishButton: {
    background: '#ed8936',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    padding: '4px 10px',
    cursor: 'pointer',
    fontSize: '13px',
    marginRight: '6px',
    whiteSpace: 'nowrap' as const,
  },
  deleteButton: {
    background: '#fc8181',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    padding: '4px 10px',
    cursor: 'pointer',
    fontSize: '13px',
    whiteSpace: 'nowrap' as const,
  },
  formCard: {
    background: '#fff',
    borderRadius: '8px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    padding: '16px',
    marginBottom: '16px',
    borderLeft: '4px solid #4299e1',
  },
  formTitle: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#333',
    marginBottom: '12px',
  },
  formGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
    gap: '12px',
    marginBottom: '12px',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '4px',
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
  },
  select: {
    border: '1px solid #e2e8f0',
    borderRadius: '4px',
    padding: '6px 10px',
    fontSize: '14px',
    color: '#333',
    outline: 'none',
    background: '#fff',
  },
  textarea: {
    border: '1px solid #e2e8f0',
    borderRadius: '4px',
    padding: '6px 10px',
    fontSize: '14px',
    color: '#333',
    outline: 'none',
    resize: 'vertical' as const,
    minHeight: '60px',
  },
  formActions: {
    display: 'flex',
    gap: '8px',
  },
  submitButton: {
    background: '#48bb78',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    padding: '8px 20px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 600,
  },
  cancelButton: {
    background: '#e2e8f0',
    color: '#718096',
    border: 'none',
    borderRadius: '6px',
    padding: '8px 20px',
    cursor: 'pointer',
    fontSize: '14px',
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
  emptyMsg: {
    color: '#718096',
    textAlign: 'center' as const,
    padding: '24px',
  },
  finishedRow: {
    opacity: 0.5,
  },
}

const OTHER_VALUE = '__other__'

export default function ReminderList() {
  const [reminders, setReminders] = useState<ReminderEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [members, setMembers] = useState<string[]>([])
  const [defaultRemindDate, setDefaultRemindDate] = useState('7,3,1')
  const [form, setForm] = useState<ReminderCreateRequest>({
    role: '',
    person: '',
    task: '',
    deadline: '',
    memo: '',
    remind_date: '7,3,1',
  })
  const [personSelectValue, setPersonSelectValue] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const fetchReminders = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.getReminders()
      setReminders(res.events ?? [])
    } catch (e) {
      setError(e instanceof Error ? e.message : '取得に失敗しました')
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchInitialData = useCallback(async () => {
    try {
      const [membersData, appSettings] = await Promise.all([
        api.getMembers(),
        api.getAppSettings(),
      ])
      setMembers(membersData)
      const remindDate = appSettings['default_remind_date'] ?? '7,3,1'
      setDefaultRemindDate(remindDate)
      setForm(prev => ({ ...prev, remind_date: remindDate }))
    } catch {
      // Non-critical: fall back to defaults silently
    }
  }, [])

  useEffect(() => {
    fetchReminders()
    fetchInitialData()
  }, [fetchReminders, fetchInitialData])

  const handleFinish = async (id: string) => {
    if (!confirm('このリマインダーを完了にしますか？')) return
    try {
      await api.finishReminder(id)
      await fetchReminders()
    } catch (e) {
      alert(e instanceof Error ? e.message : '操作に失敗しました')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('このリマインダーを削除しますか？')) return
    try {
      await api.deleteReminder(id)
      await fetchReminders()
    } catch (e) {
      alert(e instanceof Error ? e.message : '削除に失敗しました')
    }
  }

  const handleFormChange = (field: keyof ReminderCreateRequest, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  const handlePersonSelectChange = (value: string) => {
    setPersonSelectValue(value)
    if (value !== OTHER_VALUE) {
      setForm(prev => ({ ...prev, person: value }))
    } else {
      setForm(prev => ({ ...prev, person: '' }))
    }
  }

  const resetForm = () => {
    setForm({
      role: '',
      person: '',
      task: '',
      deadline: '',
      memo: '',
      remind_date: defaultRemindDate,
    })
    setPersonSelectValue('')
    setFormError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setFormError(null)
    try {
      await api.createReminder(form)
      resetForm()
      setShowForm(false)
      await fetchReminders()
    } catch (e) {
      setFormError(e instanceof Error ? e.message : '追加に失敗しました')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.header}>
          <h2 style={styles.title}>リマインダー一覧</h2>
          <button
            style={styles.addButton}
            onClick={() => setShowForm(v => !v)}
          >
            {showForm ? '✕ キャンセル' : '＋ 追加'}
          </button>
        </div>

        {error && <div style={styles.errorMsg}>{error}</div>}

        {loading ? (
          <div style={styles.emptyMsg}>読み込み中...</div>
        ) : (
          <div style={styles.tableWrapper}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>タスク</th>
                  <th style={styles.th}>担当 (役職)</th>
                  <th style={styles.th}>担当者</th>
                  <th style={styles.th}>締切日</th>
                  <th style={styles.th}>メモ</th>
                  <th style={styles.th}>リマインド日</th>
                  <th style={styles.th}>操作</th>
                </tr>
              </thead>
              <tbody>
                {reminders.length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ ...styles.td, ...styles.emptyMsg }}>
                      リマインダーはありません
                    </td>
                  </tr>
                ) : (
                  reminders.map(r => (
                    <tr key={r.id} style={r.finish ? styles.finishedRow : undefined}>
                      <td style={styles.td}>{r.task}</td>
                      <td style={styles.td}>{r.role}</td>
                      <td style={styles.td}>{r.person}</td>
                      <td style={styles.td}>{r.date}</td>
                      <td style={styles.td}>{r.memo}</td>
                      <td style={styles.td}>{r.remindDate}</td>
                      <td style={styles.td}>
                        <button
                          style={styles.finishButton}
                          onClick={() => handleFinish(r.id)}
                        >
                          完了
                        </button>
                        <button
                          style={styles.deleteButton}
                          onClick={() => handleDelete(r.id)}
                        >
                          削除
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showForm && (
        <div style={styles.formCard}>
          <div style={styles.formTitle}>新規リマインダー追加</div>
          {formError && <div style={styles.errorMsg}>{formError}</div>}
          <form onSubmit={handleSubmit}>
            <div style={styles.formGrid}>
              <div style={styles.formGroup}>
                <label style={styles.label}>役職</label>
                <input
                  style={styles.input}
                  type="text"
                  value={form.role}
                  onChange={e => handleFormChange('role', e.target.value)}
                  placeholder="例: 部長"
                  required
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>担当者</label>
                <select
                  style={styles.select}
                  value={personSelectValue}
                  onChange={e => handlePersonSelectChange(e.target.value)}
                  required={personSelectValue !== OTHER_VALUE}
                >
                  <option value="">選択してください</option>
                  {members.map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                  <option value={OTHER_VALUE}>その他 (手入力)</option>
                </select>
                {personSelectValue === OTHER_VALUE && (
                  <input
                    style={{ ...styles.input, marginTop: '6px' }}
                    type="text"
                    value={form.person}
                    onChange={e => handleFormChange('person', e.target.value)}
                    placeholder="例: 山田太郎"
                    required
                  />
                )}
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>タスク</label>
                <input
                  style={styles.input}
                  type="text"
                  value={form.task}
                  onChange={e => handleFormChange('task', e.target.value)}
                  placeholder="例: 資料提出"
                  required
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>締切日</label>
                <input
                  style={styles.input}
                  type="date"
                  value={form.deadline}
                  onChange={e => handleFormChange('deadline', e.target.value)}
                  required
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>リマインド日程</label>
                <input
                  style={styles.input}
                  type="text"
                  value={form.remind_date}
                  onChange={e => handleFormChange('remind_date', e.target.value)}
                  placeholder="例: 7,3,1"
                />
              </div>
              <div style={{ ...styles.formGroup, gridColumn: 'span 2' }}>
                <label style={styles.label}>メモ</label>
                <textarea
                  style={styles.textarea}
                  value={form.memo}
                  onChange={e => handleFormChange('memo', e.target.value)}
                  placeholder="備考など"
                />
              </div>
            </div>
            <div style={styles.formActions}>
              <button type="submit" style={styles.submitButton} disabled={submitting}>
                {submitting ? '追加中...' : '追加する'}
              </button>
              <button
                type="button"
                style={styles.cancelButton}
                onClick={() => { setShowForm(false); resetForm() }}
              >
                キャンセル
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
