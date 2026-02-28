"""LINE Webhook 署名検証."""

import base64
import hashlib
import hmac
import logging

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


async def verify_line_signature(request: Request, channel_secret: str) -> bytes:
    """LINE Webhook の署名を検証してリクエストボディを返す.

    Args:
        request: FastAPI リクエスト
        channel_secret: LINE チャンネルシークレット

    Returns:
        検証済みのリクエストボディ (bytes)

    Raises:
        HTTPException: 署名が無効な場合
    """
    body = await request.body()
    signature = request.headers.get("x-line-signature", "")

    if not signature:
        logger.warning("Missing x-line-signature header")
        raise HTTPException(status_code=403, detail="Missing signature")

    expected = base64.b64encode(
        hmac.new(channel_secret.encode(), body, hashlib.sha256).digest()
    ).decode()

    if not hmac.compare_digest(expected, signature):
        logger.warning("Invalid LINE webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    return body
