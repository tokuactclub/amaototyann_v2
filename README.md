# あまおとちゃん v3

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
FastAPI サーバー (server/app.py)
├── LINE プラットフォーム         (platforms/line/)
│   └── Webhook 受信 → 署名検証 → コマンド処理 → LINE Messaging API v3
├── Discord プラットフォーム      (platforms/discord/)
│   └── discord.py クライアント → スラッシュコマンド / discord.ext.tasks スケジューラ
├── 共通ビジネスロジック           (core/)
│   └── GAS クライアント (aiohttp 共有セッション) / コマンド処理
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
| GAS クライアント | `amaototyann/gas/` | aiohttp 共有セッションによる非同期 GAS API |
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
│   └── debug.sh
└── amaototyann/
    ├── __init__.py                   # バージョン文字列のみ
    ├── config.py                     # Pydantic BaseSettings
    ├── logging_config.py             # RotatingFileHandler ログ設定
    ├── messages.py                   # メッセージ定数
    ├── models/
    │   ├── bot.py                    # BotInfo, GroupInfo
    │   └── commands.py               # CommandResult
    ├── store/
    │   └── memory.py                 # BotStore, GroupStore
    ├── gas/
    │   └── client.py                 # aiohttp 共有セッション
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
| `GAS_URL` | Google Apps Script の Web アプリ URL。 |
| `SERVER_URL` | 本サーバー自身の公開 URL。 |
| `DISCORD_BOT_TOKEN` | Discord Bot のトークン。未設定の場合 Discord Bot は起動しない。 |

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
| `POST` | `/pushMessage` | 外部からコマンド実行 (LINE / Discord 両対応) |
| `GET` | `/backupDatabase` | DB を GAS にバックアップ |
| `GET` | `/health` | ヘルスチェック |
| `GET` | `/` | アプリログ表示 |
| `GET` | `/debug/` | デバッグ UI (debug モードのみ) |

---

## 依存関係

`pyproject.toml` で管理。主要パッケージ:

- `fastapi` + `uvicorn` — Web サーバー
- `aiohttp` — GAS API クライアント (共有セッション)
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
```bash
docker compose up app                    # 本番起動
docker compose --profile dev up app-dev  # 開発モード
docker build -t amaototyann .            # ビルドのみ
```

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
