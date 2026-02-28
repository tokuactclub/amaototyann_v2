"""プラットフォーム非依存のビジネスロジック."""

import contextlib
import logging
from datetime import UTC, datetime, timedelta, timezone

from amaototyann import messages
from amaototyann.models.commands import CommandResult
from amaototyann.sheets.client import SheetsClient

logger = logging.getLogger(__name__)


def _calculate_date_difference(dt: datetime) -> int:
    """指定の日時と現在の日時の差分 (日数) を計算する."""
    if not isinstance(dt, datetime):
        raise TypeError(f"dt must be datetime, got {type(dt)}")
    dt = dt.replace(tzinfo=UTC)
    today = datetime.now(UTC)
    return (dt - today).days


async def get_practice_events(sheets_client: SheetsClient) -> CommandResult:
    """練習予定を取得する."""
    try:
        events = await sheets_client.get_practice_events()
        logger.info("practice events: %s", events)
        if not isinstance(events, list):
            return CommandResult(error="Unexpected response from Sheets")

        formatted = []
        for x in events:
            try:
                text = messages.PRACTICE.format(
                    x["place"],
                    x["start"],
                    x["end"],
                    "\n" + x["memo"] if x["memo"] else "",
                )
            except Exception:
                text = messages.PRACTICE.format(
                    x["place"],
                    x["start"],
                    x["end"],
                    "\n" + x["memo"] if x["memo"] else "",
                )
            formatted.append(text)

        if formatted:
            return CommandResult(text="\n\n".join(formatted))
        return CommandResult(is_empty=True)
    except Exception as e:
        logger.exception("get_practice_events error")
        return CommandResult(error=str(e))


async def get_reminder_events(
    sheets_client: SheetsClient, day_left: str | None = None
) -> CommandResult:
    """リマインダー対象のイベントを取得する."""
    try:
        events = await sheets_client.get_reminders()
        if not isinstance(events, list):
            return CommandResult(error="Unexpected response from Sheets")

        result_events = []
        for event in events:
            if event["finish"] == "true":
                continue

            event["date"] = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
            event["date"] = event["date"] + timedelta(days=1) - timedelta(seconds=1)

            day_difference = _calculate_date_difference(event["date"])
            if day_difference < 0:
                continue

            target_dates: list[str] = []
            if day_left is not None:
                target_dates.append(day_left)
            else:
                target_dates = event["remindDate"].split(",")

            if str(day_difference) in target_dates:
                event["date"] = (
                    event["date"].astimezone(timezone(timedelta(hours=9))).strftime("%m/%d")
                )
                event["last_days"] = day_difference
                result_events.append(event)

        if result_events:
            return CommandResult(events=result_events)
        return CommandResult(is_empty=True)
    except Exception as e:
        logger.exception("get_reminder_events error")
        return CommandResult(error=str(e))


async def finish_event(sheets_client: SheetsClient, event_id: str) -> CommandResult:
    """リマインダー通知を終了する."""
    try:
        response = await sheets_client.finish_reminder(event_id)
        if response is not None:
            return CommandResult(text=f"{response}の通知を終わるよ！")
        return CommandResult(error="エラーで通知を終われなかったよ！ごめんね！")
    except Exception as e:
        logger.exception("finish_event error")
        return CommandResult(error=str(e))


async def get_all_reminders(sheets_client: SheetsClient) -> CommandResult:
    """全リマインダーを取得する(管理画面用、フィルタなし)."""
    try:
        events = await sheets_client.get_reminders()
        if not isinstance(events, list):
            return CommandResult(error="Unexpected response from Sheets")

        result_events = []
        for event in events:
            if event.get("finish") == "true":
                continue
            with contextlib.suppress(ValueError, KeyError):
                event["date"] = datetime.fromisoformat(
                    event["date"].replace("Z", "+00:00")
                ).strftime("%Y-%m-%d")
            result_events.append(event)

        if result_events:
            return CommandResult(events=result_events)
        return CommandResult(is_empty=True)
    except Exception as e:
        logger.exception("get_all_reminders error")
        return CommandResult(error=str(e))


async def add_practice(
    sheets_client: SheetsClient,
    date: str,
    place: str,
    start_time: str,
    end_time: str,
    memo: str = "",
) -> CommandResult:
    """練習予定を追加する."""
    try:
        success = await sheets_client.add_practice(date, place, start_time, end_time, memo)
        if success:
            return CommandResult(text="練習予定を追加しました")
        return CommandResult(error="練習予定の追加に失敗しました")
    except Exception as e:
        logger.exception("add_practice error")
        return CommandResult(error=str(e))


async def add_reminder(
    sheets_client: SheetsClient,
    deadline: str,
    role: str,
    task: str,
    person: str = "",
    memo: str = "",
    remind_date: str = "7,3,1",
) -> CommandResult:
    """リマインダーを追加する."""
    try:
        success = await sheets_client.add_reminder(deadline, role, person, task, memo, remind_date)
        if success:
            return CommandResult(text="リマインダーを追加しました")
        return CommandResult(error="リマインダーの追加に失敗しました")
    except Exception as e:
        logger.exception("add_reminder error")
        return CommandResult(error=str(e))


async def delete_event(sheets_client: SheetsClient, event_id: str) -> CommandResult:
    """カレンダーイベントを削除する."""
    try:
        result = await sheets_client.delete_practice(event_id)
        if result is None:
            result = await sheets_client.delete_reminder(event_id)
        if result is not None:
            return CommandResult(text=f"{result}を削除しました")
        return CommandResult(error="イベントの削除に失敗しました")
    except Exception as e:
        logger.exception("delete_event error")
        return CommandResult(error=str(e))
