"""asyncio.Lock で保護されたインメモリデータストア."""

import asyncio
import logging
from typing import Sequence

from amaototyann.models.bot import BotInfo, GroupInfo

logger = logging.getLogger(__name__)


class BotStore:
    """Bot 情報のインメモリストア."""

    def __init__(self) -> None:
        self._data: dict[int, BotInfo] = {}
        self._lock = asyncio.Lock()
        self._is_dirty = False

    async def load(self, bots: Sequence[BotInfo]) -> None:
        """GAS から取得した Bot 情報でストアを初期化する."""
        async with self._lock:
            self._data = {bot.id: bot for bot in bots}
            self._is_dirty = False
            logger.info("BotStore loaded %d bots", len(self._data))

    async def get(self, bot_id: int) -> BotInfo:
        """Bot ID から Bot 情報を取得."""
        async with self._lock:
            if bot_id not in self._data:
                raise KeyError(f"Bot not found: {bot_id}")
            return self._data[bot_id]

    async def list_all(self) -> list[BotInfo]:
        """全 Bot 情報を取得."""
        async with self._lock:
            return list(self._data.values())

    async def update(self, bot_id: int, **fields: object) -> BotInfo:
        """Bot 情報のフィールドを更新."""
        async with self._lock:
            if bot_id not in self._data:
                raise KeyError(f"Bot not found: {bot_id}")
            updated = self._data[bot_id].model_copy(update=fields)
            self._data[bot_id] = updated
            self._is_dirty = True
            logger.info("BotStore updated bot %d: %s", bot_id, fields)
            return updated

    @property
    def is_dirty(self) -> bool:
        return self._is_dirty

    async def mark_clean(self) -> None:
        async with self._lock:
            self._is_dirty = False

    async def dump_for_backup(self) -> list[list]:
        """GAS バックアップ用にデータをシリアライズ."""
        async with self._lock:
            return [
                [b.id, b.bot_name, b.channel_access_token,
                 b.channel_secret, b.gpt_webhook_url, b.in_group]
                for b in self._data.values()
            ]


class GroupStore:
    """グループ情報のインメモリストア."""

    def __init__(self) -> None:
        self._data: GroupInfo | None = None
        self._lock = asyncio.Lock()
        self._is_dirty = False

    async def load(self, info: GroupInfo) -> None:
        """GAS から取得したグループ情報でストアを初期化する."""
        async with self._lock:
            self._data = info
            self._is_dirty = False
            logger.info("GroupStore loaded: %s", info.group_name)

    async def get(self) -> GroupInfo:
        """グループ情報を取得."""
        async with self._lock:
            if self._data is None:
                raise ValueError("Group info not initialized")
            return self._data

    async def get_group_id(self) -> str:
        """グループ ID を返す."""
        info = await self.get()
        return info.id

    async def set_group_info(self, group_id: str, group_name: str) -> None:
        """グループ情報を設定."""
        async with self._lock:
            self._data = GroupInfo(id=group_id, group_name=group_name)
            self._is_dirty = True
            logger.info("GroupStore updated: %s (%s)", group_name, group_id)

    @property
    def is_dirty(self) -> bool:
        return self._is_dirty

    async def mark_clean(self) -> None:
        async with self._lock:
            self._is_dirty = False

    async def dump_for_backup(self) -> dict:
        """GAS バックアップ用にデータをシリアライズ."""
        async with self._lock:
            if self._data is None:
                raise ValueError("Group info not initialized")
            return {"id": self._data.id, "groupName": self._data.group_name}
