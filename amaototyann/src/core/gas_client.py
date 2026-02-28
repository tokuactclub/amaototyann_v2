"""非同期 GAS API クライアント (全プラットフォーム共通)."""
import json as _json

import aiohttp

from amaototyann.src import GAS_URL, logger


async def gas_request(payload: dict):
    """非同期 GAS 呼び出し.

    Args:
        payload: JSON payload to send to GAS (e.g. {"cmd": "practice"})

    Returns:
        Response from GAS, either parsed JSON (dict/list) or text string.
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(
            GAS_URL,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            text = await resp.text()
            try:
                return _json.loads(text)
            except (_json.JSONDecodeError, ValueError):
                return text
