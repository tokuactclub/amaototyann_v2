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
