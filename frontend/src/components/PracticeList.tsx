import { useState, useEffect, useCallback, type FormEvent } from 'react'
import { api } from '../api/client'
import type { PracticeEvent, PracticeDefault } from '../types'

export default function PracticeList() {
  const [events, setEvents] = useState<PracticeEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [practiceDefaults, setPracticeDefaults] = useState<PracticeDefault[]>([])

  const fetchEvents = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getPractice()
      setEvents(Array.isArray(data) ? data : [])
    } catch (e) {
      setError(e instanceof Error ? e.message : '取得に失敗しました')
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchDefaults = useCallback(async () => {
    try {
      const defaults = await api.getPracticeDefaults()
      setPracticeDefaults(Array.isArray(defaults) ? defaults : [])
    } catch {
      // Non-critical: fall back to empty defaults silently
    }
  }, [])

  useEffect(() => {
    fetchEvents()
    fetchDefaults()
  }, [fetchEvents, fetchDefaults])

  const handleDelete = async (eventId: number) => {
    if (!confirm('この練習予定を削除しますか？')) return
    try {
      await api.deletePractice(String(eventId))
      fetchEvents()
    } catch (e) {
      alert(e instanceof Error ? e.message : '削除に失敗しました')
    }
  }

  return (
    <div>
      <div style={styles.header}>
        <h2 style={styles.heading}>練習予定</h2>
        <button onClick={() => setShowForm(!showForm)} style={styles.addButton}>
          {showForm ? '閉じる' : '＋ 追加'}
        </button>
      </div>

      {showForm && (
        <PracticeForm
          practiceDefaults={practiceDefaults}
          onSuccess={() => { setShowForm(false); fetchEvents() }}
        />
      )}

      {error && <p style={styles.error}>{error}</p>}
      {loading ? (
        <p style={styles.loading}>読み込み中...</p>
      ) : events.length === 0 ? (
        <p style={styles.empty}>練習予定はありません</p>
      ) : (
        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>場所</th>
                <th style={styles.th}>開始</th>
                <th style={styles.th}>終了</th>
                <th style={styles.th}>メモ</th>
                <th style={styles.th}>操作</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event, i) => (
                <tr key={i}>
                  <td style={styles.td}>{event.place}</td>
                  <td style={styles.td}>{event.start}</td>
                  <td style={styles.td}>{event.end}</td>
                  <td style={styles.td}>{event.memo || '-'}</td>
                  <td style={styles.td}>
                    <button onClick={() => handleDelete(event.id)} style={styles.deleteButton}>
                      削除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function PracticeForm({
  practiceDefaults,
  onSuccess,
}: {
  practiceDefaults: PracticeDefault[]
  onSuccess: () => void
}) {
  const currentMonth = new Date().getMonth() + 1
  const monthDefault = practiceDefaults.find(d => d.month === currentMonth && d.enabled)

  const [form, setForm] = useState({
    date: new Date().toISOString().split('T')[0],
    place: monthDefault?.place ?? '',
    start_time: monthDefault?.start_time ?? '14:00',
    end_time: monthDefault?.end_time ?? '17:00',
    memo: '',
  })
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      await api.createPractice(form)
      onSuccess()
    } catch (e) {
      alert(e instanceof Error ? e.message : '追加に失敗しました')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      <div style={styles.formGrid}>
        <label style={styles.label}>
          日付
          <input type="date" value={form.date} onChange={e => setForm({...form, date: e.target.value})} style={styles.input} required />
        </label>
        <label style={styles.label}>
          場所
          <input type="text" value={form.place} onChange={e => setForm({...form, place: e.target.value})} style={styles.input} required placeholder="音楽室" />
        </label>
        <label style={styles.label}>
          開始時刻
          <input type="time" value={form.start_time} onChange={e => setForm({...form, start_time: e.target.value})} style={styles.input} required />
        </label>
        <label style={styles.label}>
          終了時刻
          <input type="time" value={form.end_time} onChange={e => setForm({...form, end_time: e.target.value})} style={styles.input} required />
        </label>
        <label style={{...styles.label, gridColumn: '1 / -1'}}>
          メモ
          <textarea value={form.memo} onChange={e => setForm({...form, memo: e.target.value})} style={{...styles.input, minHeight: '60px'}} placeholder="持ち物など" />
        </label>
      </div>
      <button type="submit" disabled={submitting} style={styles.submitButton}>
        {submitting ? '追加中...' : '練習予定を追加'}
      </button>
    </form>
  )
}

const styles: Record<string, React.CSSProperties> = {
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' },
  heading: { fontSize: '1.25rem', margin: 0 },
  addButton: { padding: '0.5rem 1rem', backgroundColor: '#48bb78', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' },
  error: { color: '#e53e3e', padding: '0.5rem' },
  loading: { color: '#718096', padding: '1rem', textAlign: 'center' as const },
  empty: { color: '#a0aec0', padding: '2rem', textAlign: 'center' as const },
  tableWrap: { overflowX: 'auto' as const },
  table: { width: '100%', borderCollapse: 'collapse' as const, fontSize: '0.875rem' },
  th: { textAlign: 'left' as const, padding: '0.5rem', borderBottom: '2px solid #e2e8f0', color: '#4a5568', fontWeight: 600 },
  td: { padding: '0.5rem', borderBottom: '1px solid #e2e8f0' },
  deleteButton: { padding: '0.25rem 0.5rem', backgroundColor: '#fc8181', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.75rem' },
  form: { backgroundColor: '#f7fafc', padding: '1rem', borderRadius: '8px', marginBottom: '1rem' },
  formGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' },
  label: { display: 'flex', flexDirection: 'column' as const, fontSize: '0.875rem', color: '#4a5568' },
  input: { marginTop: '0.25rem', padding: '0.5rem', border: '1px solid #e2e8f0', borderRadius: '4px', fontSize: '0.875rem' },
  submitButton: { marginTop: '0.75rem', padding: '0.5rem 1.5rem', backgroundColor: '#4299e1', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' },
}
