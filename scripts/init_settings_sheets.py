"""新設定シートの初期データ投入スクリプト.

Usage:
    uv run python scripts/init_settings_sheets.py

必要な環境変数 (.env または shell):
    GOOGLE_SERVICE_ACCOUNT_JSON  - サービスアカウント JSON 文字列
    GOOGLE_SPREADSHEET_ID        - スプレッドシート ID
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from amaototyann.config import get_settings
from amaototyann.sheets.client import SheetsClient

# 徳島演技クラブ メンバー一覧 (プレースホルダー: 実行時に実際の名前に差し替えること)
DEFAULT_MEMBERS = [
    "青木",
    "石田",
    "井上",
    "上田",
    "岡田",
    "加藤",
    "金子",
    "木村",
    "黒田",
    "佐々木",
    "佐藤",
    "鈴木",
    "高橋",
    "田中",
    "中村",
    "西田",
    "野口",
    "橋本",
    "林",
    "藤田",
    "松本",
    "三浦",
    "村上",
    "山口",
    "山田",
    "渡辺",
]

# 月別練習デフォルト設定
DEFAULT_PRACTICE_DEFAULTS = [
    {
        "month": m,
        "enabled": True,
        "place": "ふれあい健康館",
        "start_time": "14:00",
        "end_time": "17:00",
    }
    for m in range(1, 13)
]

# アプリ設定
DEFAULT_APP_SETTINGS = {
    "default_remind_date": "7,3,1",
}


async def main() -> None:
    """新設定シートに初期データを投入する."""
    settings = get_settings()

    if not settings.google_service_account_json:
        print("ERROR: GOOGLE_SERVICE_ACCOUNT_JSON が設定されていません。")
        sys.exit(1)
    if not settings.google_spreadsheet_id:
        print("ERROR: GOOGLE_SPREADSHEET_ID が設定されていません。")
        sys.exit(1)

    print("新設定シートの初期データを投入します...")
    print(f"  スプレッドシート ID: {settings.google_spreadsheet_id}")

    # SheetsClient は同期コンストラクタのため executor 経由で初期化する
    loop = asyncio.get_running_loop()
    client: SheetsClient = await loop.run_in_executor(
        None,
        SheetsClient,
        settings.google_service_account_json,
        settings.google_spreadsheet_id,
    )

    # --- members シート ---
    ok = await client.set_members(DEFAULT_MEMBERS)
    print(f"  members ({len(DEFAULT_MEMBERS)} 件): {'OK' if ok else 'FAILED'}")

    # --- practice_defaults シート ---
    ok = await client.set_practice_defaults(DEFAULT_PRACTICE_DEFAULTS)
    print(f"  practice_defaults ({len(DEFAULT_PRACTICE_DEFAULTS)} 件): {'OK' if ok else 'FAILED'}")

    # --- app_settings シート ---
    for key, value in DEFAULT_APP_SETTINGS.items():
        ok = await client.set_app_setting(key, value)
        print(f"  app_settings[{key}] = {value!r}: {'OK' if ok else 'FAILED'}")

    print("完了!")


if __name__ == "__main__":
    asyncio.run(main())
