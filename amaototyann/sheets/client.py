"""Google Sheets 直接アクセスクライアント (GAS 代替)."""

import asyncio
import json
import logging
import uuid
from functools import partial
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_SHEET_NAMES = (
    "practice",
    "reminder",
    "bot_info",
    "group_info",
    "members",
    "practice_defaults",
    "app_settings",
)


class SheetsClient:
    """gspread ベースの Google Sheets クライアント.

    GAS HTTP ミドルウェアを置き換え、スプレッドシートに直接アクセスする。
    gspread は同期ライブラリのため、全メソッドを asyncio executor 経由で非同期化する。
    """

    def __init__(self, credentials_json: str, spreadsheet_id: str) -> None:
        """サービスアカウント認証でスプレッドシートを開く."""
        info = json.loads(credentials_json)
        creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
        gc = gspread.authorize(creds)
        self._spreadsheet = gc.open_by_key(spreadsheet_id)
        self._ws: dict[str, gspread.Worksheet] = {
            name: self._spreadsheet.worksheet(name) for name in _SHEET_NAMES
        }
        logger.info("SheetsClient 初期化完了 (spreadsheet=%s)", spreadsheet_id)

    # ------------------------------------------------------------------
    # ヘルパー
    # ------------------------------------------------------------------

    async def _run_sync(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """同期関数を asyncio executor で実行する."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    # ------------------------------------------------------------------
    # practice シート
    # ------------------------------------------------------------------

    async def get_practice_events(self) -> list[dict]:
        """練習予定を全件取得する.

        返却キー: id, date, place, start, end, memo
        (後方互換のため startTime/endTime ではなく start/end を使用)
        """
        try:
            records = await self._run_sync(self._ws["practice"].get_all_records)
            return [
                {
                    "id": str(r["id"]),
                    "date": str(r["date"]),
                    "place": str(r["place"]),
                    "start": str(r["startTime"]),
                    "end": str(r["endTime"]),
                    "memo": str(r.get("memo", "")),
                }
                for r in records
            ]
        except Exception:
            logger.exception("get_practice_events 失敗")
            return []

    async def add_practice(
        self, date: str, place: str, start_time: str, end_time: str, memo: str = ""
    ) -> bool:
        """練習予定を追加する."""
        try:
            row = [str(uuid.uuid4()), date, place, start_time, end_time, memo]
            await self._run_sync(self._ws["practice"].append_row, row)
            logger.info("練習予定を追加: %s %s", date, place)
            return True
        except Exception:
            logger.exception("add_practice 失敗")
            return False

    async def delete_practice(self, event_id: str) -> str | None:
        """練習予定を ID で削除する. 削除した場所名を返す."""
        try:
            cell = await self._run_sync(self._ws["practice"].find, event_id)
            if cell is None:
                logger.warning("練習予定が見つからない: %s", event_id)
                return None
            row_values = await self._run_sync(self._ws["practice"].row_values, cell.row)
            place = row_values[2] if len(row_values) > 2 else ""
            await self._run_sync(self._ws["practice"].delete_rows, cell.row)
            logger.info("練習予定を削除: %s (%s)", event_id, place)
            return place
        except Exception:
            logger.exception("delete_practice 失敗: %s", event_id)
            return None

    # ------------------------------------------------------------------
    # reminder シート
    # ------------------------------------------------------------------

    async def get_reminders(self) -> list[dict]:
        """リマインダーを全件取得する.

        返却キー: id, date, role, person, task, memo, remindDate, finish
        (後方互換のため deadline ではなく date を使用)
        """
        try:
            records = await self._run_sync(self._ws["reminder"].get_all_records)
            return [
                {
                    "id": str(r["id"]),
                    "date": str(r["deadline"]),
                    "role": str(r["role"]),
                    "person": str(r["person"]),
                    "task": str(r["task"]),
                    "memo": str(r.get("memo", "")),
                    "remindDate": str(r.get("remindDate", "")),
                    "finish": str(r.get("finish", "false")).lower(),
                }
                for r in records
            ]
        except Exception:
            logger.exception("get_reminders 失敗")
            return []

    async def add_reminder(
        self,
        deadline: str,
        role: str,
        person: str,
        task: str,
        memo: str,
        remind_date: str,
    ) -> bool:
        """リマインダーを追加する."""
        try:
            row = [str(uuid.uuid4()), deadline, role, person, task, memo, remind_date, "FALSE"]
            await self._run_sync(self._ws["reminder"].append_row, row)
            logger.info("リマインダーを追加: %s %s", deadline, task)
            return True
        except Exception:
            logger.exception("add_reminder 失敗")
            return False

    async def finish_reminder(self, event_id: str) -> str | None:
        """リマインダーを完了にする. finish 列を TRUE に更新し、タスク名を返す."""
        try:
            cell = await self._run_sync(self._ws["reminder"].find, event_id)
            if cell is None:
                logger.warning("リマインダーが見つからない: %s", event_id)
                return None
            row_values = await self._run_sync(self._ws["reminder"].row_values, cell.row)
            task_name = row_values[4] if len(row_values) > 4 else ""
            await self._run_sync(self._ws["reminder"].update_cell, cell.row, 8, "TRUE")
            logger.info("リマインダーを完了: %s (%s)", event_id, task_name)
            return task_name
        except Exception:
            logger.exception("finish_reminder 失敗: %s", event_id)
            return None

    async def delete_reminder(self, event_id: str) -> str | None:
        """リマインダーを ID で削除する. タスク名を返す."""
        try:
            cell = await self._run_sync(self._ws["reminder"].find, event_id)
            if cell is None:
                logger.warning("リマインダーが見つからない: %s", event_id)
                return None
            row_values = await self._run_sync(self._ws["reminder"].row_values, cell.row)
            task_name = row_values[4] if len(row_values) > 4 else ""
            await self._run_sync(self._ws["reminder"].delete_rows, cell.row)
            logger.info("リマインダーを削除: %s (%s)", event_id, task_name)
            return task_name
        except Exception:
            logger.exception("delete_reminder 失敗: %s", event_id)
            return None

    # ------------------------------------------------------------------
    # bot_info シート
    # ------------------------------------------------------------------

    async def get_bot_info(self) -> list[list]:
        """Bot 情報を全件取得する (ヘッダー除外).

        返却形式: [[0, "name", "token", "secret", "gpt_url", true], ...]
        """
        try:
            rows = await self._run_sync(self._ws["bot_info"].get_all_values)
            return rows[1:] if len(rows) > 1 else []
        except Exception:
            logger.exception("get_bot_info 失敗")
            return []

    async def set_bot_info(self, data: list[list]) -> bool:
        """Bot 情報を全件置換する (ヘッダーは保持)."""
        try:
            ws = self._ws["bot_info"]
            all_values = await self._run_sync(ws.get_all_values)
            row_count = len(all_values)
            if row_count > 1:
                await self._run_sync(ws.delete_rows, 2, row_count)
            if data:
                await self._run_sync(
                    ws.update,
                    data,
                    f"A2:{gspread.utils.rowcol_to_a1(len(data) + 1, len(data[0]))}",
                )
            logger.info("Bot 情報を更新 (%d 件)", len(data))
            return True
        except Exception:
            logger.exception("set_bot_info 失敗")
            return False

    # ------------------------------------------------------------------
    # group_info シート
    # ------------------------------------------------------------------

    async def get_group_info(self) -> dict | None:
        """グループ情報を取得する."""
        try:
            records = await self._run_sync(self._ws["group_info"].get_all_records)
            if not records:
                return None
            r = records[0]
            return {"id": str(r["id"]), "groupName": str(r["groupName"])}
        except Exception:
            logger.exception("get_group_info 失敗")
            return None

    async def set_group_info(self, data: dict) -> bool:
        """グループ情報を設定する (1 行のみ)."""
        try:
            ws = self._ws["group_info"]
            all_values = await self._run_sync(ws.get_all_values)
            row = [str(data.get("id", "")), str(data.get("groupName", ""))]
            if len(all_values) > 1:
                await self._run_sync(ws.update, [row], "A2:B2")
            else:
                await self._run_sync(ws.append_row, row)
            logger.info("グループ情報を更新: %s", data.get("groupName", ""))
            return True
        except Exception:
            logger.exception("set_group_info 失敗")
            return False

    # ------------------------------------------------------------------
    # members シート
    # ------------------------------------------------------------------

    async def get_members(self) -> list[str]:
        """メンバー名一覧を取得する."""
        try:
            rows = await self._run_sync(self._ws["members"].get_all_values)
            return [row[0] for row in rows if row and row[0]]
        except Exception:
            logger.exception("get_members 失敗")
            return []

    async def set_members(self, names: list[str]) -> bool:
        """メンバー名一覧を全件置換する."""
        try:
            ws = self._ws["members"]
            await self._run_sync(ws.clear)
            if names:
                cells = [[name] for name in names]
                await self._run_sync(ws.update, "A1", cells)
            logger.info("メンバーを更新 (%d 件)", len(names))
            return True
        except Exception:
            logger.exception("set_members 失敗")
            return False

    # ------------------------------------------------------------------
    # practice_defaults シート
    # ------------------------------------------------------------------

    async def get_practice_defaults(self) -> list[dict]:
        """月別練習デフォルト設定を全件取得する.

        返却キー: month, enabled, place, start_time, end_time
        """
        try:
            rows = await self._run_sync(self._ws["practice_defaults"].get_all_values)
            results = []
            for row in rows:
                if len(row) >= 5:
                    results.append(
                        {
                            "month": int(row[0]),
                            "enabled": row[1].upper() == "TRUE",
                            "place": row[2],
                            "start_time": row[3],
                            "end_time": row[4],
                        }
                    )
            return results
        except Exception:
            logger.exception("get_practice_defaults 失敗")
            return []

    async def set_practice_defaults(self, data: list[dict]) -> bool:
        """月別練習デフォルト設定を全件置換する."""
        try:
            ws = self._ws["practice_defaults"]
            await self._run_sync(ws.clear)
            if data:
                cells = [
                    [
                        str(d["month"]),
                        str(d["enabled"]).upper(),
                        d["place"],
                        d["start_time"],
                        d["end_time"],
                    ]
                    for d in data
                ]
                await self._run_sync(ws.update, "A1", cells)
            logger.info("練習デフォルトを更新 (%d 件)", len(data))
            return True
        except Exception:
            logger.exception("set_practice_defaults 失敗")
            return False

    # ------------------------------------------------------------------
    # app_settings シート
    # ------------------------------------------------------------------

    async def get_app_settings(self) -> dict[str, str]:
        """アプリ設定を全件取得する (key → value マップ)."""
        try:
            rows = await self._run_sync(self._ws["app_settings"].get_all_values)
            return {row[0]: row[1] for row in rows if len(row) >= 2 and row[0]}
        except Exception:
            logger.exception("get_app_settings 失敗")
            return {}

    async def set_app_setting(self, key: str, value: str) -> bool:
        """アプリ設定を 1 件更新する. キーが存在しない場合は末尾に追記する."""
        try:
            ws = self._ws["app_settings"]
            rows = await self._run_sync(ws.get_all_values)
            for i, row in enumerate(rows):
                if row and row[0] == key:
                    await self._run_sync(ws.update_cell, i + 1, 2, value)
                    logger.info("アプリ設定を更新: %s = %s", key, value)
                    return True
            # キーが未存在のため末尾に追記
            next_row = len(rows) + 1
            await self._run_sync(ws.update, f"A{next_row}", [[key, value]])
            logger.info("アプリ設定を追加: %s = %s", key, value)
            return True
        except Exception:
            logger.exception("set_app_setting 失敗: %s", key)
            return False
