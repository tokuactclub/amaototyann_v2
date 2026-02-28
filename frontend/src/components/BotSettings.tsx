import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { BotInfo, GroupInfo } from '../types'

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
  botsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
    gap: '16px',
    marginBottom: '24px',
  },
  botCard: {
    background: '#fff',
    borderRadius: '8px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    padding: '16px',
    borderTop: '3px solid #4299e1',
  },
  botName: {
    fontSize: '16px',
    fontWeight: 700,
    color: '#333',
    marginBottom: '8px',
  },
  badge: {
    display: 'inline-block',
    padding: '2px 10px',
    borderRadius: '12px',
    fontSize: '12px',
    fontWeight: 600,
    marginBottom: '12px',
  },
  badgeGreen: {
    background: '#c6f6d5',
    color: '#276749',
  },
  badgeGray: {
    background: '#e2e8f0',
    color: '#718096',
  },
  fieldRow: {
    marginBottom: '8px',
  },
  fieldLabel: {
    fontSize: '12px',
    color: '#718096',
    fontWeight: 600,
    marginBottom: '2px',
  },
  fieldValueRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  fieldValue: {
    fontSize: '13px',
    color: '#333',
    fontFamily: 'monospace',
    background: '#f7fafc',
    padding: '4px 8px',
    borderRadius: '4px',
    border: '1px solid #e2e8f0',
    flex: 1,
    wordBreak: 'break-all' as const,
    overflow: 'hidden',
  },
  maskedValue: {
    fontSize: '13px',
    color: '#718096',
    fontFamily: 'monospace',
    background: '#f7fafc',
    padding: '4px 8px',
    borderRadius: '4px',
    border: '1px solid #e2e8f0',
    flex: 1,
    letterSpacing: '2px',
  },
  toggleButton: {
    background: 'none',
    border: '1px solid #e2e8f0',
    borderRadius: '4px',
    padding: '3px 8px',
    cursor: 'pointer',
    fontSize: '12px',
    color: '#718096',
    whiteSpace: 'nowrap' as const,
  },
  groupSection: {
    marginTop: '8px',
  },
  groupRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    flexWrap: 'wrap' as const,
    gap: '8px',
  },
  groupInfo: {
    flex: 1,
  },
  groupName: {
    fontSize: '18px',
    fontWeight: 700,
    color: '#333',
    marginBottom: '4px',
  },
  groupId: {
    fontSize: '13px',
    color: '#718096',
    fontFamily: 'monospace',
  },
  editButton: {
    background: '#4299e1',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    padding: '6px 14px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 600,
    alignSelf: 'flex-start',
  },
  formCard: {
    background: '#f7fafc',
    border: '1px solid #e2e8f0',
    borderRadius: '6px',
    padding: '12px',
    marginTop: '12px',
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
  formActions: {
    display: 'flex',
    gap: '8px',
    marginTop: '4px',
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
  cancelButton: {
    background: '#e2e8f0',
    color: '#718096',
    border: 'none',
    borderRadius: '6px',
    padding: '7px 18px',
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
  loadingMsg: {
    color: '#718096',
    padding: '16px',
    textAlign: 'center' as const,
  },
  emptyMsg: {
    color: '#718096',
    padding: '16px',
    textAlign: 'center' as const,
  },
}

// --- Masked field sub-component ---
function MaskedField({ value, label }: { value: string; label: string }) {
  const [visible, setVisible] = useState(false)
  return (
    <div style={styles.fieldRow}>
      <div style={styles.fieldLabel}>{label}</div>
      <div style={styles.fieldValueRow}>
        {visible ? (
          <span style={styles.fieldValue}>{value}</span>
        ) : (
          <span style={styles.maskedValue}>{'●'.repeat(Math.min(value.length, 20))}</span>
        )}
        <button style={styles.toggleButton} onClick={() => setVisible(v => !v)}>
          {visible ? '隠す' : '表示'}
        </button>
      </div>
    </div>
  )
}

// --- Bot card sub-component ---
function BotCard({ bot }: { bot: BotInfo }) {
  return (
    <div style={styles.botCard}>
      <div style={styles.botName}>{bot.bot_name}</div>
      <span
        style={{
          ...styles.badge,
          ...(bot.in_group ? styles.badgeGreen : styles.badgeGray),
        }}
      >
        {bot.in_group ? 'グループ参加中' : '未参加'}
      </span>
      <MaskedField label="Channel Access Token" value={bot.channel_access_token} />
      <MaskedField label="Channel Secret" value={bot.channel_secret} />
      <div style={styles.fieldRow}>
        <div style={styles.fieldLabel}>GPT Webhook URL</div>
        <div style={styles.fieldValue}>{bot.gpt_webhook_url || '—'}</div>
      </div>
    </div>
  )
}

// --- Group edit form ---
interface GroupEditFormProps {
  initial: GroupInfo
  onSave: () => void
  onCancel: () => void
}

function GroupEditForm({ initial, onSave, onCancel }: GroupEditFormProps) {
  const [id, setId] = useState(initial.id)
  const [groupName, setGroupName] = useState(initial.group_name)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await api.updateGroup({ id, groupName })
      onSave()
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新に失敗しました')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={styles.formCard}>
      {error && <div style={styles.errorMsg}>{error}</div>}
      <form onSubmit={handleSubmit}>
        <div style={styles.formGroup}>
          <label style={styles.label}>グループ ID</label>
          <input
            style={styles.input}
            type="text"
            value={id}
            onChange={e => setId(e.target.value)}
            required
          />
        </div>
        <div style={styles.formGroup}>
          <label style={styles.label}>グループ名</label>
          <input
            style={styles.input}
            type="text"
            value={groupName}
            onChange={e => setGroupName(e.target.value)}
            required
          />
        </div>
        <div style={styles.formActions}>
          <button type="submit" style={styles.submitButton} disabled={submitting}>
            {submitting ? '保存中...' : '保存'}
          </button>
          <button type="button" style={styles.cancelButton} onClick={onCancel}>
            キャンセル
          </button>
        </div>
      </form>
    </div>
  )
}

// --- Main component ---
export default function BotSettings() {
  const [bots, setBots] = useState<BotInfo[]>([])
  const [botsLoading, setBotsLoading] = useState(true)
  const [botsError, setBotsError] = useState<string | null>(null)

  const [group, setGroup] = useState<GroupInfo | null>(null)
  const [groupLoading, setGroupLoading] = useState(true)
  const [groupError, setGroupError] = useState<string | null>(null)
  const [editingGroup, setEditingGroup] = useState(false)

  const fetchBots = useCallback(async () => {
    setBotsLoading(true)
    setBotsError(null)
    try {
      const data = await api.getBots()
      setBots(data)
    } catch (e) {
      setBotsError(e instanceof Error ? e.message : '取得に失敗しました')
    } finally {
      setBotsLoading(false)
    }
  }, [])

  const fetchGroup = useCallback(async () => {
    setGroupLoading(true)
    setGroupError(null)
    try {
      const data = await api.getGroup()
      setGroup(data)
    } catch (e) {
      setGroupError(e instanceof Error ? e.message : '取得に失敗しました')
    } finally {
      setGroupLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchBots()
    fetchGroup()
  }, [fetchBots, fetchGroup])

  const handleGroupSave = async () => {
    setEditingGroup(false)
    await fetchGroup()
  }

  return (
    <div style={styles.container}>
      {/* Bot 情報 */}
      <h2 style={styles.sectionTitle}>Bot 情報</h2>
      {botsError && <div style={styles.errorMsg}>{botsError}</div>}
      {botsLoading ? (
        <div style={styles.loadingMsg}>読み込み中...</div>
      ) : bots.length === 0 ? (
        <div style={styles.emptyMsg}>Bot が登録されていません</div>
      ) : (
        <div style={styles.botsGrid}>
          {bots.map(bot => (
            <BotCard key={bot.id} bot={bot} />
          ))}
        </div>
      )}

      {/* グループ情報 */}
      <h2 style={styles.sectionTitle}>グループ情報</h2>
      <div style={styles.card}>
        {groupError && <div style={styles.errorMsg}>{groupError}</div>}
        {groupLoading ? (
          <div style={styles.loadingMsg}>読み込み中...</div>
        ) : group ? (
          <div style={styles.groupSection}>
            <div style={styles.groupRow}>
              <div style={styles.groupInfo}>
                <div style={styles.groupName}>{group.group_name}</div>
                <div style={styles.groupId}>ID: {group.id}</div>
              </div>
              {!editingGroup && (
                <button style={styles.editButton} onClick={() => setEditingGroup(true)}>
                  編集
                </button>
              )}
            </div>
            {editingGroup && (
              <GroupEditForm
                initial={group}
                onSave={handleGroupSave}
                onCancel={() => setEditingGroup(false)}
              />
            )}
          </div>
        ) : (
          <div style={styles.emptyMsg}>グループ情報がありません</div>
        )}
      </div>
    </div>
  )
}
