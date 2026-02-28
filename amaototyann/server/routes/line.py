"""LINE Webhook ルーター."""

import json
import logging

from fastapi import APIRouter, Request, HTTPException

from amaototyann.server.lifespan import bot_store, group_store
from amaototyann.platforms.line.webhook_handler import handle_line_webhook

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/lineWebhook/{bot_id}")
async def line_webhook(bot_id: int, request: Request):
    """LINE の Webhook を受け取るエンドポイント."""
    logger.info("Received LINE webhook for bot %d", bot_id)
    try:
        return await handle_line_webhook(request, bot_id, bot_store, group_store)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Bot not found: {bot_id}")
    except Exception as e:
        logger.exception("LINE webhook error")
        raise HTTPException(status_code=500, detail="Internal server error")
