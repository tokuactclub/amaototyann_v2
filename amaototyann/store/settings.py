"""設定情報のインメモリストア."""

import asyncio
import logging

from amaototyann.models.settings import PracticeDefault

logger = logging.getLogger(__name__)


class SettingsStore:
    """設定情報のインメモリストア."""

    def __init__(self) -> None:
        self._members: list[str] = []
        self._practice_defaults: list[PracticeDefault] = []
        self._app_settings: dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._is_dirty = False

    async def load(
        self,
        members: list[str],
        practice_defaults: list[PracticeDefault],
        app_settings: dict[str, str],
    ) -> None:
        """GAS から取得した設定情報でストアを初期化する."""
        async with self._lock:
            self._members = list(members)
            self._practice_defaults = list(practice_defaults)
            self._app_settings = dict(app_settings)
            self._is_dirty = False
            logger.info(
                "SettingsStore loaded: %d members, %d practice defaults, %d app settings",
                len(self._members),
                len(self._practice_defaults),
                len(self._app_settings),
            )

    async def get_members(self) -> list[str]:
        """メンバー名のリストを取得."""
        async with self._lock:
            return list(self._members)

    async def set_members(self, names: list[str]) -> None:
        """メンバー名のリストを設定."""
        async with self._lock:
            self._members = list(names)
            self._is_dirty = True
            logger.info("SettingsStore updated members: %d members", len(names))

    def get_practice_default(self, month: int) -> PracticeDefault | None:
        """指定月の練習デフォルト設定を取得."""
        for d in self._practice_defaults:
            if d.month == month:
                return d
        return None

    async def get_practice_defaults(self) -> list[PracticeDefault]:
        """全練習デフォルト設定を取得."""
        async with self._lock:
            return list(self._practice_defaults)

    async def set_practice_defaults(self, defaults: list[PracticeDefault]) -> None:
        """練習デフォルト設定を設定."""
        async with self._lock:
            self._practice_defaults = list(defaults)
            self._is_dirty = True
            logger.info(
                "SettingsStore updated practice defaults: %d defaults",
                len(defaults),
            )

    def get_setting(self, key: str, default: str = "") -> str:
        """アプリケーション設定値を取得."""
        return self._app_settings.get(key, default)

    async def set_setting(self, key: str, value: str) -> None:
        """アプリケーション設定値を設定."""
        async with self._lock:
            self._app_settings[key] = value
            self._is_dirty = True
            logger.info("SettingsStore updated setting: %s", key)

    async def get_all_settings(self) -> dict[str, str]:
        """全アプリケーション設定を取得."""
        async with self._lock:
            return dict(self._app_settings)

    @property
    def is_dirty(self) -> bool:
        return self._is_dirty

    async def mark_clean(self) -> None:
        """ダーティフラグをクリア."""
        async with self._lock:
            self._is_dirty = False

    async def dump_for_backup(self) -> dict[str, object]:
        """GAS バックアップ用にデータをシリアライズ."""
        async with self._lock:
            return {
                "members": list(self._members),
                "practiceDefaults": [d.model_dump() for d in self._practice_defaults],
                "appSettings": dict(self._app_settings),
            }
