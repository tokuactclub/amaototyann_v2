"""データモデル."""

from amaototyann.models.bot import BotInfo, GroupInfo
from amaototyann.models.commands import CommandResult
from amaototyann.models.schedule import PracticeCreate, ReminderCreate

__all__ = ["BotInfo", "CommandResult", "GroupInfo", "PracticeCreate", "ReminderCreate"]
