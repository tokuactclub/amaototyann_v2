"""非同期 GAS API クライアント (共有セッション)."""

import json as _json
import logging

import aiohttp

from amaototyann.config import get_settings
from amaototyann.models.bot import BotInfo, GroupInfo

logger = logging.getLogger(__name__)

_session: aiohttp.ClientSession | None = None


async def _get_session() -> aiohttp.ClientSession:
    """共有 aiohttp セッションを取得する."""
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
        )
    return _session


async def close_session() -> None:
    """共有セッションを閉じる."""
    global _session
    if _session and not _session.closed:
        await _session.close()
        _session = None


async def gas_request(payload: dict) -> dict | list | str:
    """GAS API に非同期リクエストを送信する."""
    settings = get_settings()
    session = await _get_session()
    async with session.post(settings.gas_url, json=payload) as resp:
        text = await resp.text()
        try:
            return _json.loads(text)
        except (_json.JSONDecodeError, ValueError):
            return text


async def fetch_bot_info() -> list[BotInfo]:
    """GAS から Bot 情報を取得して BotInfo リストを返す."""
    for attempt in range(3):
        try:
            data = await gas_request({"cmd": "getBotInfo"})
            if not isinstance(data, list):
                logger.error("Unexpected getBotInfo response: %s", data)
                continue
            return [
                BotInfo(
                    id=row[0],
                    bot_name=row[1],
                    channel_access_token=row[2],
                    channel_secret=row[3],
                    gpt_webhook_url=row[4],
                    in_group=row[5],
                )
                for row in data
            ]
        except Exception as e:
            logger.error("Failed to fetch bot info (attempt %d): %s", attempt + 1, e)
    return []


async def fetch_group_info() -> GroupInfo | None:
    """GAS からグループ情報を取得して GroupInfo を返す."""
    for attempt in range(3):
        try:
            data = await gas_request({"cmd": "getGroupInfo"})
            if not isinstance(data, dict):
                logger.error("Unexpected getGroupInfo response: %s", data)
                continue
            return GroupInfo(id=data["id"], group_name=data["groupName"])
        except Exception as e:
            logger.error("Failed to fetch group info (attempt %d): %s", attempt + 1, e)
    return None


async def backup_bot_info(bot_data: list[list]) -> bool:
    """Bot 情報を GAS にバックアップする."""
    try:
        response = await gas_request(
            {
                "cmd": "setBotInfo",
                "options": {"bot_info": bot_data},
            }
        )
        if response == "success":
            logger.info("Bot info backup success")
            return True
        logger.error("Bot info backup failed: %s", response)
        return False
    except Exception as e:
        logger.error("Bot info backup error: %s", e)
        return False


async def backup_group_info(group_data: dict) -> bool:
    """グループ情報を GAS にバックアップする."""
    try:
        response = await gas_request(
            {
                "cmd": "setGroupInfo",
                "options": group_data,
            }
        )
        if response == "success":
            logger.info("Group info backup success")
            return True
        logger.error("Group info backup failed: %s", response)
        return False
    except Exception as e:
        logger.error("Group info backup error: %s", e)
        return False
