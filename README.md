# あまおとちゃん

徳島 ACT クラブ（あまおと）向けのリマインダー・練習通知 Bot です。
LINE Bot と Discord Bot を単一の FastAPI サーバーで同時に稼働させる統合アーキテクチャを採用しています。

---

## プロジェクト概要

Google Apps Script (GAS) に登録されたイベント情報・練習予定を取得し、LINE グループおよび Discord サーバーへ通知を送信します。

主な機能:

- 練習予定の通知 (毎日 JST 08:00 に自動送信 / 手動コマンド)
- タスクのリマインダー通知 (毎日 JST 20:00 に自動送信 / 手動コマンド)
- リマインダー通知の完了処理
- 引き継ぎ資料・SNS リンクの送信

---

## アーキテクチャ

```
FastAPI サーバー (server.py)
├── LINE プラットフォーム         (platforms/line/)
│   └── Webhook 受信 → コマンド処理 → LINE API
├── Discord プラットフォーム      (platforms/discord/)
│   └── discord.py クライアント → スラッシュコマンド / スケジューラ
└── 共通ビジネスロジック           (core/)
    └── GAS クライアント / コマンド処理
```

### 各レイヤーの役割

| レイヤー | パス | 役割 |
|---|---|---|
| コアロジック | `amaototyann/src/core/` | プラットフォーム非依存のビジネスロジック。GAS への非同期リクエスト、イベント取得・整形処理を担う。 |
| LINE 統合 | `amaototyann/src/platforms/line/` | LINE Webhook の受信・解析、Flex Message (バブルメッセージ) の生成、LINE Messaging API への送信。 |
| Discord 統合 | `amaototyann/src/platforms/discord/` | discord.py クライアント、スラッシュコマンド定義、`discord.ext.tasks` による定時スケジューラ、UI コンポーネント (ボタン等)。 |
| サーバー | `amaototyann/src/server.py` | FastAPI アプリ本体。`lifespan` で Discord クライアントの起動/停止とバックアップループを管理。LINE Webhook・Push Message・バックアップの各エンドポイントを提供。 |

---

## ディレクトリ構成

```
amaototyann_v2/
├── amaototyann/
│   ├── src/
│   │   ├── core/
│   │   │   ├── commands.py          # プラットフォーム非依存コマンド (get_practice_events 等)
│   │   │   └── gas_client.py        # 非同期 GAS API クライアント
│   │   ├── platforms/
│   │   │   ├── discord/
│   │   │   │   ├── client.py        # Discord Bot クライアント・スケジューラ定義
│   │   │   │   ├── commands.py      # スラッシュコマンド定義 (DiscordCommands)
│   │   │   │   ├── message_sender.py# メッセージ送信ユーティリティ
│   │   │   │   └── ui.py            # UI コンポーネント (ProgressButton 等)
│   │   │   └── line/
│   │   │       ├── bubble_msg.py    # Flex Message (バブルメッセージ) 定義
│   │   │       ├── client.py        # LINE Messaging API クライアント
│   │   │       ├── converter.py     # レスポンス変換ユーティリティ
│   │   │       └── webhook_handler.py # LINE Webhook イベント処理
│   │   ├── database.py              # ローカル DB (ボット設定・グループ情報)
│   │   ├── messages.py              # メッセージテンプレート定数
│   │   └── server.py                # FastAPI アプリ・エンドポイント定義
│   ├── debug/                       # デバッグ用ツール (Webhook 送信 UI)
│   └── logs/
│       └── app.log
├── scripts/
│   ├── start.sh                     # 本番起動スクリプト
│   └── debug.sh                     # 開発用起動スクリプト (--reload)
├── requirements.txt
├── .env.example
└── .python-version
```

---

## 環境変数

`.env.example` を参考に `.env` を作成してください。

| 変数名 | 説明 |
|---|---|
| `IS_RENDER_SERVER` | Render 環境で動作する場合は `True`。ローカルは `False`。 |
| `GAS_URL` | Google Apps Script の Web アプリ URL。イベント取得・更新に使用。 |
| `SERVER_URL` | 本サーバー自身の公開 URL。GAS からのコールバック等に使用。 |
| `DISCORD_BOT_TOKEN` | Discord Bot のトークン。未設定の場合 Discord Bot は起動しない。 |

---

## 起動方法

### 本番環境

```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

サーバーは `http://0.0.0.0:8000` で起動します。

### 開発環境 (ホットリロード)

```bash
chmod +x scripts/debug.sh
./scripts/debug.sh
```

ポート 8000 で既に起動中のプロセスを自動的に終了してから `--reload` オプション付きで起動します。

### 主なエンドポイント

| メソッド | パス | 説明 |
|---|---|---|
| `POST` | `/lineWebhook/{bot_id}` | LINE Webhook 受信 |
| `POST` | `/pushMessage` | 外部からコマンド実行 (LINE / Discord 両対応) |
| `GET` | `/backupDatabase` | DB を GAS にバックアップ |
| `GET` | `/health` | ヘルスチェック (Discord 接続状態含む) |
| `GET` | `/` | アプリログ表示 |

---

## 依存関係

```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
aiohttp>=3.8.0
requests==2.31.0
line-bot-sdk==1.20.0
discord.py>=2.0
python-dotenv
```

---

## Discord コマンド一覧

スラッシュコマンドとして登録されます。

| コマンド | 説明 |
|---|---|
| `/help` | 利用可能なコマンド一覧を表示 |
| `/reminder` | リマインダーを手動送信 |
| `/practice` | 練習予定を手動送信 |
| `/finish` | リマインダー通知を完了状態にする |
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

グループ内でテキストメッセージとして送信します。

| コマンド | 説明 |
|---|---|
| `!help` | コマンド一覧の Flex Message を送信 |
| `!reminder` | リマインダーを手動送信 |
| `!practice` | 練習予定を送信 |
| `!place` | 練習場所を送信 (未実装) |
| `!handover` | 引き継ぎ資料の URL を送信 |
| `!changeGroup` | リマインダー送信対象グループを変更 |
| `!finish {id}` | 指定 ID のリマインダー通知を完了状態にする |
