# あまおとちゃん v3

徳島 ACT クラブ（あまおと）向けのリマインダー・練習通知 Bot です。
LINE Bot と Discord Bot を単一の FastAPI サーバーで同時に稼働させる統合アーキテクチャを採用しています。

---

## プロジェクト概要

Google スプレッドシートに登録されたイベント情報・練習予定を取得し、LINE グループおよび Discord サーバーへ通知を送信します。

主な機能:

- 練習予定の通知 (毎日 JST 08:00 に自動送信 / 手動コマンド)
- タスクのリマインダー通知 (毎日 JST 20:00 に自動送信 / 手動コマンド)
- リマインダー通知の完了処理
- 引き継ぎ資料・SNS リンクの送信
- GPT チャットボット転送: LINE メッセージが「あまおとちゃん」で始まる場合、BotInfo の `gpt_webhook_url` に Webhook を転送

---

## アーキテクチャ

```
FastAPI サーバー (server/app.py)
├── LINE プラットフォーム         (platforms/line/)
│   └── Webhook 受信 → 署名検証 → コマンド処理 → LINE Messaging API v3
├── Discord プラットフォーム      (platforms/discord/)
│   └── discord.py クライアント → スラッシュコマンド / discord.ext.tasks スケジューラ
├── 共通ビジネスロジック           (core/)
│   └── Sheets クライアント (gspread / サービスアカウント認証) / コマンド処理
├── データストア                  (store/)
│   └── asyncio.Lock 付きインメモリ DB (Pydantic モデル)
└── デバッグツール                (debug/)
    └── FastAPI ルーター (debug モード時のみ有効)
```

### 各レイヤーの役割

| レイヤー | パス | 役割 |
|---|---|---|
| 設定 | `amaototyann/config.py` | Pydantic BaseSettings による環境変数管理 |
| モデル | `amaototyann/models/` | BotInfo, GroupInfo, CommandResult (Pydantic モデル) |
| ストア | `amaototyann/store/` | asyncio.Lock 付きインメモリデータストア |
| Sheets クライアント | `amaototyann/sheets/` | gspread + google-auth サービスアカウントによる Google Sheets API 直接アクセス |
| コアロジック | `amaototyann/core/` | プラットフォーム非依存のビジネスロジック |
| LINE 統合 | `amaototyann/platforms/line/` | Webhook 署名検証 (HMAC-SHA256)、line-bot-sdk v3 async |
| Discord 統合 | `amaototyann/platforms/discord/` | @tree.command 直接定義、discord.ext.tasks スケジューラ |
| サーバー | `amaototyann/server/` | App Factory、lifespan ライフサイクル管理 |
| デバッグ | `amaototyann/debug/` | FastAPI ルーターによる Webhook テスト UI |

---

## ディレクトリ構成

```
amaototyann_v2/
├── pyproject.toml                    # 依存関係・ビルド設定
├── .env.example
├── .python-version                   # 3.12
├── README.md
├── scripts/
│   ├── start.sh
│   ├── debug.sh
│   └── init_settings_sheets.py   # 設定シート初期データ投入
└── amaototyann/
    ├── __init__.py                   # バージョン文字列のみ
    ├── config.py                     # Pydantic BaseSettings
    ├── logging_config.py             # RotatingFileHandler ログ設定
    ├── messages.py                   # メッセージ定数
    ├── models/
    │   ├── bot.py                    # BotInfo, GroupInfo
    │   ├── commands.py               # CommandResult
    │   └── settings.py               # PracticeDefault 月別練習デフォルト
    ├── store/
    │   ├── memory.py                 # BotStore, GroupStore
    │   └── settings.py               # SettingsStore 設定管理ストア
    ├── sheets/
    │   └── client.py                 # gspread サービスアカウント認証クライアント
    ├── core/
    │   └── commands.py               # ビジネスロジック
    ├── platforms/
    │   ├── line/
    │   │   ├── security.py           # 署名検証 (HMAC-SHA256)
    │   │   ├── webhook_handler.py    # イベントディスパッチャ
    │   │   ├── commands.py           # LineCommandHandler
    │   │   ├── flex_messages.py      # Flex Message ビルダー
    │   │   └── converter.py          # 日本語変換
    │   └── discord/
    │       ├── bot.py                # Client + discord.ext.tasks
    │       ├── commands.py           # @tree.command 定義
    │       ├── message_sender.py     # DiscordSender
    │       └── ui.py                 # ProgressButton
    ├── server/
    │   ├── app.py                    # FastAPI App Factory
    │   ├── lifespan.py               # 起動/停止管理
    │   └── routes/
    │       ├── line.py               # /lineWebhook/{bot_id}
    │       ├── push.py               # /pushMessage
    │       └── admin.py              # /health, /backupDatabase, /
    └── debug/
        ├── router.py                 # FastAPI ルーター
        └── templates/
```

---

## 環境変数

`.env.example` を参考に `.env` を作成してください。

| 変数名 | 説明 |
|---|---|
| `IS_RENDER_SERVER` | Render 環境で動作する場合は `True`。ローカルは `False`。 |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Google サービスアカウントの認証情報 JSON 文字列。Sheets API アクセスに使用。 |
| `GOOGLE_SPREADSHEET_ID` | データ管理用 Google スプレッドシートの ID。 |
| `SERVER_URL` | 本サーバー自身の公開 URL。 |
| `DISCORD_BOT_TOKEN` | Discord Bot のトークン。未設定の場合 Discord Bot は起動しない。 |
| `ADMIN_PASSWORD` | 管理画面のアクセスパスワード。未設定の場合は認証なし。 |
| `ADMIN_TOKEN` | `ADMIN_PASSWORD` が未設定の場合のフォールバック。旧バージョンとの後方互換性のために受け付ける。`ADMIN_PASSWORD` が優先される。 |

---

## 起動方法

### 本番環境

```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

### 開発環境 (ホットリロード)

```bash
chmod +x scripts/debug.sh
./scripts/debug.sh
```

### 主なエンドポイント

| メソッド | パス | 説明 |
|---|---|---|
| `POST` | `/lineWebhook/{bot_id}` | LINE Webhook 受信 (署名検証付き) |
| `POST` | `/pushMessage` | 外部からコマンド実行 (LINE / Discord 両対応)。`/pushMessage/` (末尾スラッシュ付き) も受け付ける |
| `GET` | `/backupDatabase` | DB を Google スプレッドシートにバックアップ |
| `GET` | `/health` | ヘルスチェック |
| `GET` | `/test` | ヘルスチェック (`/health` のエイリアス) |
| `GET` | `/` | アプリログ表示 |
| `GET` | `/debug/` | デバッグ UI (debug モードのみ) |
| `GET` | `/api/admin/settings/members` | メンバー一覧取得 |
| `PUT` | `/api/admin/settings/members` | メンバー一覧更新 |
| `GET` | `/api/admin/settings/practice-defaults` | 練習デフォルト取得 |
| `PUT` | `/api/admin/settings/practice-defaults` | 練習デフォルト更新 |
| `GET` | `/api/admin/settings/app` | アプリ設定取得 |
| `PUT` | `/api/admin/settings/app` | アプリ設定更新 |

---

## 依存関係

`pyproject.toml` で管理。主要パッケージ:

- `fastapi` + `uvicorn` — Web サーバー
- `gspread` — Google Sheets API クライアント
- `google-auth` — Google サービスアカウント認証
- `aiohttp` — 非同期 HTTP クライアント (汎用)
- `line-bot-sdk>=3.11` — LINE Messaging API v3 (async 対応)
- `discord.py>=2.4` — Discord Bot
- `pydantic-settings` — 環境変数管理
- `httpx` — デバッグ用 async HTTP クライアント
- `jinja2` — デバッグ UI テンプレート

---

## Discord コマンド一覧

| コマンド | 説明 |
|---|---|
| `/help` | 利用可能なコマンド一覧を表示 |
| `/reminder` | リマインダーを手動送信 |
| `/practice` | 練習予定を手動送信 |
| `/finish event_id` | リマインダー通知を完了状態にする |
| `/place` | 練習場所を送信 (未実装) |
| `/handover` | 引き継ぎ資料の URL を送信 |
| `/youtube` | YouTube の URL を送信 |
| `/instagram` | Instagram の URL を送信 |
| `/twitter` | Twitter の URL を送信 |
| `/homepage` | ホームページの URL を送信 |

自動送信スケジュール:

- JST 08:00 - 練習通知 (`/practice` 相当)
- JST 20:00 - リマインダー通知 (`/reminder` 相当)

---

## LINE コマンド一覧

| コマンド | 説明 |
|---|---|
| `!help` | コマンド一覧を送信 |
| `!reminder` | リマインダーを手動送信 |
| `!practice` | 練習予定を送信 |
| `!place` | 練習場所を送信 (未実装) |
| `!handover` | 引き継ぎ資料の URL を送信 |
| `!changeGroup` | リマインダー送信対象グループを変更 |
| `!finish {id}` | 指定 ID のリマインダー通知を完了状態にする |

---

## v3 での主な改善点

- **セキュリティ**: LINE Webhook の HMAC-SHA256 署名検証を追加
- **完全 async**: 同期 I/O ブロック (requests.post) を排除、aiohttp 共有セッション
- **型安全性**: Pydantic モデルによるデータバリデーション
- **line-bot-sdk v3**: EOL の v1 から async 対応の v3 に移行
- **God Module 解体**: `__init__.py` を config, logging, store, gas に分割
- **壊れたコマンド修正**: Discord `/finish` に event_id パラメータ追加、LINE `!changeGroup` のバグ修正
- **デバッグツール修復**: Flask → FastAPI ルーターに移行
- **エラーハンドリング統一**: `CommandResult` 境界でデータ化する1パターン
- **モダン Python**: Python 3.12+, pyproject.toml, Pydantic BaseSettings
- **GPT 転送復旧**: LINE メッセージが「あまおとちゃん」で始まる場合に `gpt_webhook_url` へ転送する機能を復旧
- **BotStore add/delete**: ランタイムでの Bot 追加・削除メソッドを BotStore に追加
- **後方互換性**: `ADMIN_TOKEN` 環境変数を `ADMIN_PASSWORD` のフォールバックとして受け付け、`/pushMessage/` (末尾スラッシュ付き) にも対応
- **エンドポイント復旧**: `GET /test` ヘルスチェックエンドポイントを復旧

---

## 開発環境

### 必要なツール
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — パッケージマネージャー

### セットアップ
```bash
uv sync          # 依存関係インストール
```

### 開発コマンド
```bash
# サーバー起動
./scripts/start.sh          # 本番モード
./scripts/debug.sh          # 開発モード（ホットリロード）

# コード品質
./scripts/lint.sh           # ruff format + ruff check + ty check
uv run ruff format .        # フォーマット
uv run ruff check --fix .   # リント（自動修正）
uv run ty check amaototyann/ # 型チェック

# テスト
uv run pytest tests/ -v                    # テスト実行
uv run pytest tests/ -v --cov             # カバレッジ付き
uv run pytest tests/ -v --cov --cov-report=html  # HTMLレポート
```

### Docker

**3-Stage Multi-Platform Build:**
- Stage 1: `node:22-slim` — React フロントエンド (TypeScript) をビルド
- Stage 2: `python:3.12-slim` — Python 依存関係をインストール (uv 使用)
- Stage 3: `python:3.12-slim` — runtime (frontend/dist + Python コード)

**本番起動:**
```bash
docker compose up app  # ポート 8000 (backend のみ)
```

**開発環境 (ホットリロード):**
```bash
docker compose --profile dev up  # backend (port 8000) + frontend dev (port 5173)
```

frontend-dev サービスは `npm run dev -- --host 0.0.0.0` で起動し、5173 ポートでホットリロード対応の開発サーバーを提供します。

**ビルドのみ:**
```bash
docker build -t amaototyann .
```

**参考:**
- `package-lock.json` は reproducible builds のため git で追跡
- Render デプロイ用の blueprint は `render.yaml` を参照

### Pre-commit
```bash
uv run pre-commit install   # Git hooks インストール
```

### CI/CD
GitHub Actions で以下を自動実行:
- `ruff format --check` — フォーマットチェック
- `ruff check` — リント
- `ty check` — 型チェック（warning のみ）
- `pytest --cov` — テスト + カバレッジ

---

## 設定管理

### メンバー管理

管理画面からメンバー（ニックネーム）の追加・削除ができます。
登録されたメンバーはリマインダー作成時の担当者ドロップダウンに表示されます。

### 月別練習デフォルト

月ごとに練習の ON/OFF、デフォルトの場所・開始時刻・終了時刻を設定できます。
練習予定を新規追加する際に、当月のデフォルト値が自動的にフォームにプリフィルされます。

### アプリ設定

リマインドのデフォルト日数（例: `7,3,1` = 7日前・3日前・1日前）などの設定を管理画面から変更できます。

### Google スプレッドシートのシート構成

| シート名 | 列構成 | 説明 |
|----------|--------|------|
| `practice` | id, date, place, start, end, memo | 練習予定 |
| `reminder` | id, date, role, person, task, memo, remindDate, finish | リマインダー |
| `bot_info` | id, bot_name, channel_access_token, channel_secret, gpt_webhook_url, in_group | Bot 設定 |
| `group_info` | id, groupName | グループ情報 |
| `members` | name | メンバー一覧 |
| `practice_defaults` | month, enabled, place, start_time, end_time | 月別練習デフォルト |
| `app_settings` | key, value | アプリ設定 |

### 初期データ投入

新しい設定シートに初期データを投入するスクリプト:

```bash
uv run python scripts/init_settings_sheets.py
```

実行前にスプレッドシートに `members`, `practice_defaults`, `app_settings` の3シートを手動で作成してください。

---

## デプロイメント

### Render へのデプロイ

`render.yaml` Blueprint を使用して簡単にデプロイできます:

1. [Render Dashboard](https://dashboard.render.com/) にログイン
2. "Blueprint" → "Connect Repository" で本リポジトリを接続
3. 以下の環境変数を設定:
   - `GOOGLE_SERVICE_ACCOUNT_JSON` — Google サービスアカウントの認証情報 JSON 文字列
   - `GOOGLE_SPREADSHEET_ID` — データ管理用 Google スプレッドシートの ID
   - `DISCORD_BOT_TOKEN` — Discord Bot トークン (オプション)
   - `ADMIN_PASSWORD` — 管理画面アクセスパスワード (オプション)
   - `IS_RENDER_SERVER` — 自動で `True` に設定
4. Deploy を実行

Render は自動で Dockerfile の 3-stage build を実行し、本番環境で必要な依存関係のみを含むイメージをビルドします。

---

## 管理画面 (Admin Panel)

スプレッドシートの代わりに、Web ブラウザから練習予定・リマインダーを管理できます。

### アクセス

- URL: `https://<your-server>/admin/`
- 認証: 環境変数 `ADMIN_PASSWORD` に設定したパスワードでログイン

### 機能

- **練習予定**: 一覧表示・新規追加・削除
- **リマインダー**: 一覧表示・新規追加・完了・削除
- **Bot 設定**: Bot 情報の確認・グループ情報の編集
- **設定管理**: メンバー管理・月別練習デフォルト・アプリ設定 (リマインドデフォルト日数等)

### 環境変数

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `ADMIN_PASSWORD` | いいえ | 管理画面のアクセスパスワード。未設定の場合は認証なし |
| `ADMIN_TOKEN` | いいえ | `ADMIN_PASSWORD` が未設定の場合のフォールバック (後方互換) |

### フロントエンドビルド

```bash
cd frontend
npm install
npm run build
```

### Google スプレッドシートの設定

管理画面および Bot が使用するデータは Google スプレッドシートで管理します。
サービスアカウントをスプレッドシートの編集者として共有し、`GOOGLE_SERVICE_ACCOUNT_JSON` と `GOOGLE_SPREADSHEET_ID` を環境変数に設定してください。

GAS の時間主導型トリガー (`trigger.gs`) は引き続き `/pushMessage/` エンドポイントに POST することで定期通知を起動します。
データの読み書きは Python が Google Sheets API (gspread + サービスアカウント) を通じて直接行うため、GAS を HTTP 中継として使用する必要はありません。
