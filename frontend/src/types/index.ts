export interface PracticeEvent {
  id: number
  place: string
  start: string
  end: string
  memo: string
}

export interface ReminderEvent {
  id: string
  role: string
  person: string
  task: string
  memo: string
  date: string
  remindDate: string
  finish: string
}

export interface PracticeCreateRequest {
  date: string
  place: string
  start_time: string
  end_time: string
  memo: string
}

export interface ReminderCreateRequest {
  deadline: string
  role: string
  person: string
  task: string
  memo: string
  remind_date: string
}

export interface BotInfo {
  id: number
  bot_name: string
  channel_access_token: string
  channel_secret: string
  gpt_webhook_url: string
  in_group: boolean
}

export interface GroupInfo {
  id: string
  group_name: string
}

export interface ApiResponse<T = unknown> {
  data?: T
  error?: string
}

export interface PracticeDefault {
  month: number
  enabled: boolean
  place: string
  start_time: string
  end_time: string
}

export interface AppSettings {
  [key: string]: string
}
