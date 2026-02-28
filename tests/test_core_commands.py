"""Tests for amaototyann.core.commands business logic."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amaototyann.core.commands import (
    _calculate_date_difference,
    finish_event,
    get_practice_events,
    get_reminder_events,
)
from amaototyann.models.commands import CommandResult


def _make_mock_sheets_client(**method_overrides: AsyncMock) -> MagicMock:
    """SheetsClient のモックを生成するヘルパー."""
    mock = MagicMock()
    for method_name, async_mock in method_overrides.items():
        setattr(mock, method_name, async_mock)
    return mock


# ---------------------------------------------------------------------------
# _calculate_date_difference
# ---------------------------------------------------------------------------


class TestCalculateDateDifference:
    def test_future_date_returns_positive(self) -> None:
        future = datetime.now(UTC) + timedelta(days=5)
        diff = _calculate_date_difference(future)
        assert diff >= 4  # Allow slight sub-second drift

    def test_past_date_returns_negative(self) -> None:
        past = datetime.now(UTC) - timedelta(days=3)
        diff = _calculate_date_difference(past)
        assert diff < 0

    def test_today_returns_zero_or_negative(self) -> None:
        # "today" without time component can be 0 or -1 depending on current time
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        diff = _calculate_date_difference(today)
        assert diff in {0, -1}

    def test_exactly_one_day_ahead(self) -> None:
        tomorrow = datetime.now(UTC) + timedelta(days=1)
        diff = _calculate_date_difference(tomorrow)
        assert diff == 0 or diff == 1  # timedelta.days truncates fractions

    def test_non_datetime_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="dt must be datetime"):
            _calculate_date_difference("2025-01-01")  # type: ignore[arg-type]

    def test_naive_datetime_is_accepted(self) -> None:
        # The function replaces tzinfo with UTC internally
        naive = datetime(2099, 12, 31)
        diff = _calculate_date_difference(naive)
        assert diff > 0


# ---------------------------------------------------------------------------
# get_practice_events
# ---------------------------------------------------------------------------


class TestGetPracticeEvents:
    async def test_returns_formatted_text_for_valid_events(self) -> None:
        mock_events = [
            {
                "place": "音楽室",
                "start": "14:00",
                "end": "17:00",
                "memo": "",
            }
        ]
        mock_client = _make_mock_sheets_client(
            get_practice_events=AsyncMock(return_value=mock_events),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await get_practice_events()

        assert isinstance(result, CommandResult)
        assert result.text is not None
        assert "音楽室" in result.text
        assert result.error is None
        assert result.is_empty is False

    async def test_time_values_used_directly(self) -> None:
        # SheetsClient returns HH:MM strings directly (no split needed)
        mock_events = [
            {
                "place": "体育館",
                "start": "09:30",
                "end": "12:00",
                "memo": "持ち物: 水筒",
            }
        ]
        mock_client = _make_mock_sheets_client(
            get_practice_events=AsyncMock(return_value=mock_events),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await get_practice_events()

        assert result.text is not None
        assert "09:30" in result.text
        assert "12:00" in result.text
        assert "持ち物: 水筒" in result.text

    async def test_memo_empty_string_omits_newline(self) -> None:
        mock_events = [
            {
                "place": "ホール",
                "start": "13:00",
                "end": "16:00",
                "memo": "",
            }
        ]
        mock_client = _make_mock_sheets_client(
            get_practice_events=AsyncMock(return_value=mock_events),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await get_practice_events()

        assert result.text is not None
        # memo is empty: the trailing "\n{memo}" branch is skipped
        assert result.text.endswith("")  # no trailing newline from memo

    async def test_multiple_events_joined_with_double_newline(self) -> None:
        mock_events = [
            {
                "place": "A棟",
                "start": "10:00",
                "end": "12:00",
                "memo": "",
            },
            {
                "place": "B棟",
                "start": "14:00",
                "end": "16:00",
                "memo": "",
            },
        ]
        mock_client = _make_mock_sheets_client(
            get_practice_events=AsyncMock(return_value=mock_events),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await get_practice_events()

        assert result.text is not None
        assert "\n\n" in result.text
        assert "A棟" in result.text
        assert "B棟" in result.text

    async def test_empty_list_returns_is_empty(self) -> None:
        mock_client = _make_mock_sheets_client(
            get_practice_events=AsyncMock(return_value=[]),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await get_practice_events()

        assert result.is_empty is True
        assert result.text is None
        assert result.error is None

    async def test_sheets_client_raises_exception_returns_error(self) -> None:
        mock_client = _make_mock_sheets_client(
            get_practice_events=AsyncMock(side_effect=RuntimeError("network failure")),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await get_practice_events()

        assert result.error == "network failure"
        assert result.text is None


# ---------------------------------------------------------------------------
# get_reminder_events
# ---------------------------------------------------------------------------


class TestGetReminderEvents:
    def _make_future_event(
        self,
        *,
        days_ahead: int = 7,
        remind_dates: str = "7,3,1",
        finish: str = "false",
        memo: str = "",
    ) -> dict:
        """Helper to build a reminder event dict.

        The function under test applies ``+1 day - 1 second`` to the raw ISO date
        before calling ``_calculate_date_difference``.  Passing ``datetime.now(UTC)
        + timedelta(days=days_ahead)`` as the raw date therefore produces a final
        ``day_difference`` equal to exactly ``days_ahead`` (timedelta.days truncates
        the sub-second remainder).
        """
        dt = datetime.now(UTC) + timedelta(days=days_ahead)
        return {
            "date": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "remindDate": remind_dates,
            "finish": finish,
            "title": "テストイベント",
            "memo": memo,
        }

    async def test_event_matching_day_left_is_returned(self) -> None:
        event = self._make_future_event(days_ahead=7)
        mock_client = _make_mock_sheets_client(
            get_reminders=AsyncMock(return_value=[event]),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await get_reminder_events(day_left="7")

        assert result.events is not None
        assert len(result.events) == 1
        assert result.is_empty is False

    async def test_event_not_matching_day_left_is_filtered(self) -> None:
        event = self._make_future_event(days_ahead=5)
        mock_client = _make_mock_sheets_client(
            get_reminders=AsyncMock(return_value=[event]),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await get_reminder_events(day_left="7")

        assert result.is_empty is True
        assert result.events is None

    async def test_finished_event_is_skipped(self) -> None:
        event = self._make_future_event(days_ahead=7, finish="true")
        mock_client = _make_mock_sheets_client(
            get_reminders=AsyncMock(return_value=[event]),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await get_reminder_events(day_left="7")

        assert result.is_empty is True

    async def test_past_event_is_skipped(self) -> None:
        # date already in the past after +1day adjustment
        past_dt = datetime.now(UTC) - timedelta(days=3)
        event = {
            "date": past_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "remindDate": "0",
            "finish": "false",
            "title": "過去のイベント",
        }
        mock_client = _make_mock_sheets_client(
            get_reminders=AsyncMock(return_value=[event]),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await get_reminder_events(day_left="0")

        assert result.is_empty is True

    async def test_no_day_left_uses_remind_date_field(self) -> None:
        # When day_left is None the function reads remindDate from each event
        event = self._make_future_event(days_ahead=3, remind_dates="3,7")
        mock_client = _make_mock_sheets_client(
            get_reminders=AsyncMock(return_value=[event]),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await get_reminder_events()  # day_left=None

        assert result.events is not None
        assert len(result.events) == 1

    async def test_no_day_left_does_not_match_non_listed_date(self) -> None:
        event = self._make_future_event(days_ahead=5, remind_dates="7,1")
        mock_client = _make_mock_sheets_client(
            get_reminders=AsyncMock(return_value=[event]),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await get_reminder_events()

        assert result.is_empty is True

    async def test_event_date_is_formatted_as_mm_dd(self) -> None:
        event = self._make_future_event(days_ahead=7)
        mock_client = _make_mock_sheets_client(
            get_reminders=AsyncMock(return_value=[event]),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await get_reminder_events(day_left="7")

        assert result.events is not None
        # date should be formatted as MM/DD (JST)
        date_str: str = result.events[0]["date"]
        assert "/" in date_str
        assert len(date_str) == 5  # "MM/DD"

    async def test_last_days_field_is_set(self) -> None:
        event = self._make_future_event(days_ahead=7)
        mock_client = _make_mock_sheets_client(
            get_reminders=AsyncMock(return_value=[event]),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await get_reminder_events(day_left="7")

        assert result.events is not None
        assert result.events[0]["last_days"] == 7

    async def test_empty_list_returns_is_empty(self) -> None:
        mock_client = _make_mock_sheets_client(
            get_reminders=AsyncMock(return_value=[]),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await get_reminder_events(day_left="7")

        assert result.is_empty is True

    async def test_sheets_client_raises_exception_returns_error(self) -> None:
        mock_client = _make_mock_sheets_client(
            get_reminders=AsyncMock(side_effect=ConnectionError("timeout")),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await get_reminder_events()

        assert result.error == "timeout"
        assert result.events is None

    async def test_multiple_events_mixed_filter(self) -> None:
        events = [
            self._make_future_event(days_ahead=7),  # should match day_left="7"
            self._make_future_event(days_ahead=3),  # should NOT match
            self._make_future_event(days_ahead=7, finish="true"),  # finished, skip
        ]
        mock_client = _make_mock_sheets_client(
            get_reminders=AsyncMock(return_value=events),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await get_reminder_events(day_left="7")

        assert result.events is not None
        assert len(result.events) == 1

    async def test_remind_date_with_comma_separated_values(self) -> None:
        # remindDate="7,3,1" and days_ahead=3 → should match "3"
        event = self._make_future_event(days_ahead=3, remind_dates="7,3,1")
        mock_client = _make_mock_sheets_client(
            get_reminders=AsyncMock(return_value=[event]),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await get_reminder_events()

        assert result.events is not None
        assert result.events[0]["last_days"] == 3


# ---------------------------------------------------------------------------
# finish_event
# ---------------------------------------------------------------------------


class TestFinishEvent:
    async def test_successful_finish_returns_text_with_task_name(self) -> None:
        mock_client = _make_mock_sheets_client(
            finish_reminder=AsyncMock(return_value="定期演奏会"),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await finish_event("event-123")

        assert result.text == "定期演奏会の通知を終わるよ！"
        assert result.error is None

    async def test_none_response_returns_error(self) -> None:
        mock_client = _make_mock_sheets_client(
            finish_reminder=AsyncMock(return_value=None),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await finish_event("event-999")

        assert result.error == "エラーで通知を終われなかったよ！ごめんね！"
        assert result.text is None

    async def test_sheets_client_called_with_correct_id(self) -> None:
        mock_finish = AsyncMock(return_value="イベント名")
        mock_client = _make_mock_sheets_client(finish_reminder=mock_finish)
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            await finish_event("abc-789")

        mock_finish.assert_called_once_with("abc-789")

    async def test_sheets_client_raises_exception_returns_error(self) -> None:
        mock_client = _make_mock_sheets_client(
            finish_reminder=AsyncMock(side_effect=ValueError("bad id")),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await finish_event("bad")

        assert result.error == "bad id"
        assert result.text is None

    async def test_empty_string_response_treated_as_success(self) -> None:
        # "" is not None, so it goes through the success branch
        mock_client = _make_mock_sheets_client(
            finish_reminder=AsyncMock(return_value=""),
        )
        with patch("amaototyann.core.commands._get_sheets_client", return_value=mock_client):
            result = await finish_event("x")

        assert result.text == "の通知を終わるよ！"
        assert result.error is None
