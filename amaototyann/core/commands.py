"""プラットフォーム非依存のビジネスロジック."""

import logging
from datetime import UTC, datetime, timedelta, timezone

from amaototyann import messages
from amaototyann.gas.client import gas_request
from amaototyann.models.commands import CommandResult

logger = logging.getLogger(__name__)


def _calculate_date_difference(dt: datetime) -> int:
    """指定の日時と現在の日時の差分 (日数) を計算する."""
    if not isinstance(dt, datetime):
        raise TypeError(f"dt must be datetime, got {type(dt)}")
    dt = dt.replace(tzinfo=UTC)
    today = datetime.now(UTC)
    return (dt - today).days


async def get_practice_events() -> CommandResult:
    """練習予定を取得する."""
    try:
        events = await gas_request({"cmd": "practice"})
        logger.info("practice events: %s", events)
        if not isinstance(events, list):
            return CommandResult(error="Unexpected response from GAS")

        formatted = []
        for x in events:
            try:
                text = messages.PRACTICE.format(
                    x["place"],
                    x["start"].split()[3][:-3],
                    x["end"].split()[3][:-3],
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


async def get_reminder_events(day_left: str | None = None) -> CommandResult:
    """リマインダー対象のイベントを取得する."""
    try:
        events = await gas_request({"cmd": "reminder"})
        if not isinstance(events, list):
            return CommandResult(error="Unexpected response from GAS")

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


async def finish_event(event_id: str) -> CommandResult:
    """リマインダー通知を終了する."""
    try:
        response = await gas_request({"cmd": "finish", "options": {"id": event_id}})
        task_name = response if isinstance(response, str) else str(response)
        if task_name != "error":
            return CommandResult(text=f"{task_name}の通知を終わるよ！")
        return CommandResult(error="エラーで通知を終われなかったよ！ごめんね！")
    except Exception as e:
        logger.exception("finish_event error")
        return CommandResult(error=str(e))


async def get_all_reminders() -> CommandResult:
    """全リマインダーを取得する（管理画面用、フィルタなし）."""
    try:
        events = await gas_request({"cmd": "reminder"})
        if not isinstance(events, list):
            return CommandResult(error="Unexpected response from GAS")

        result_events = []
        for event in events:
            if event.get("finish") == "true":
                continue
            try:
                event["date"] = datetime.fromisoformat(
                    event["date"].replace("Z", "+00:00")
                ).strftime("%Y-%m-%d")
            except (ValueError, KeyError):
                pass
            result_events.append(event)

        if result_events:
            return CommandResult(events=result_events)
        return CommandResult(is_empty=True)
    except Exception as e:
        logger.exception("get_all_reminders error")
        return CommandResult(error=str(e))


async def add_practice(date: str, place: str, start_time: str, end_time: str, memo: str = "") -> CommandResult:
    """練習予定を追加する."""
    try:
        response = await gas_request({
            "cmd": "addPractice",
            "options": {
                "date": date,
                "place": place,
                "startTime": start_time,
                "endTime": end_time,
                "memo": memo,
            },
        })
        if response == "success":
            return CommandResult(text="練習予定を追加しました")
        return CommandResult(error="練習予定の追加に失敗しました")
    except Exception as e:
        logger.exception("add_practice error")
        return CommandResult(error=str(e))


async def add_reminder(deadline: str, role: str, task: str, person: str = "", memo: str = "", remind_date: str = "7,3,1") -> CommandResult:
    """リマインダーを追加する."""
    try:
        response = await gas_request({
            "cmd": "addReminder",
            "options": {
                "deadline": deadline,
                "role": role,
                "person": person,
                "task": task,
                "memo": memo,
                "remindDate": remind_date,
            },
        })
        if response == "success":
            return CommandResult(text="リマインダーを追加しました")
        return CommandResult(error="リマインダーの追加に失敗しました")
    except Exception as e:
        logger.exception("add_reminder error")
        return CommandResult(error=str(e))


async def delete_event(event_id: str) -> CommandResult:
    """カレンダーイベントを削除する."""
    try:
        response = await gas_request({"cmd": "deleteEvent", "options": {"id": event_id}})
        if isinstance(response, str) and "削除" in response:
            return CommandResult(text=response)
        return CommandResult(error="イベントの削除に失敗しました")
    except Exception as e:
        logger.exception("delete_event error")
        return CommandResult(error=str(e))
