import type { PracticeEvent, PracticeCreateRequest, ReminderEvent, ReminderCreateRequest, BotInfo, GroupInfo } from '../types'

const API_BASE = '/api/admin'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (res.status === 401) {
    throw new Error('Unauthorized')
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `HTTP ${res.status}`)
  }

  return res.json()
}

export const api = {
  // Auth
  login: (token: string) =>
    request<{ ok: boolean }>('/login', {
      method: 'POST',
      body: JSON.stringify({ token }),
    }),

  logout: () =>
    request<{ ok: boolean }>('/logout', { method: 'POST' }),

  checkAuth: () =>
    request<{ authenticated: boolean }>('/me'),

  // Practice
  getPractice: () =>
    request<PracticeEvent[]>('/practice'),

  createPractice: (data: PracticeCreateRequest) =>
    request<{ text?: string; error?: string }>('/practice', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deletePractice: (eventId: string) =>
    request<{ text?: string; error?: string }>(`/practice/${encodeURIComponent(eventId)}`, {
      method: 'DELETE',
    }),

  // Reminder
  getReminders: () =>
    request<{ events?: ReminderEvent[]; is_empty?: boolean }>('/reminder'),

  createReminder: (data: ReminderCreateRequest) =>
    request<{ text?: string; error?: string }>('/reminder', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  finishReminder: (eventId: string) =>
    request<{ text?: string; error?: string }>(`/reminder/${encodeURIComponent(eventId)}/finish`, {
      method: 'POST',
    }),

  deleteReminder: (eventId: string) =>
    request<{ text?: string; error?: string }>(`/reminder/${encodeURIComponent(eventId)}`, {
      method: 'DELETE',
    }),

  // Bot Settings
  getBots: () =>
    request<BotInfo[]>('/bots'),

  updateBots: (data: unknown[][]) =>
    request<{ text?: string; error?: string }>('/bots', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  getGroup: () =>
    request<GroupInfo>('/group'),

  updateGroup: (data: { id: string; groupName: string }) =>
    request<{ text?: string; error?: string }>('/group', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
}
